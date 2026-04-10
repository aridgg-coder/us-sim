%% TUSX MATLAB Launcher for k-Wave Acoustic Simulation
% 
% This script serves as the main entry point for running TUSX simulations
% from the Python backend. It reads a JSON handoff package, prepares the
% simulation environment, runs k-Wave-based acoustic propagation, and
% writes results back to JSON for the backend to consume.
%
% Expected environment:
%   - TUSX toolbox on MATLAB path
%   - k-Wave toolbox on MATLAB path
%   - Input JSON at TUSX_INPUT_FILE environment variable
%
% Output:
%   - tusx_result.json in the same directory as the input JSON

function tusx_matlab_launcher()
    % MATLAB -batch does not expose argv like Octave; read paths from env.
    input_file = getenv('TUSX_INPUT_FILE');
    run_dir = getenv('TUSX_RUN_DIR');
    
    % Initialize environment
    initialize_tusx_environment();
    
    % Validate inputs
    if isempty(input_file) || ~isfile(input_file)
        error('Input file not found: %s', input_file);
    end
    if isempty(run_dir) || ~isfolder(run_dir)
        error('Run directory not found: %s', run_dir);
    end
    
    try
        % Read the handoff JSON
        json_text = fileread(input_file);
        input_data = jsondecode(json_text);
        
        % Extract simulation parameters
        [simulation_result, metadata] = run_tusx_simulation(input_data);
        
        % Build result structure
        result = struct();
        result.schema_version = 'tusx-result-v1';
        result.job_id = input_data.job_id;
        result.status = 'success';
        result.created_at_utc = datetime('now', 'TimeZone', 'UTC');
        result.grayscale_image_url = simulation_result.grayscale_image_url;
        result.summary = simulation_result.summary;
        result.path_segments = simulation_result.path_segments;
        result.region_hits = simulation_result.region_hits;
        result.simulation_metadata = metadata;
        
        % Write result to JSON
        output_file = fullfile(run_dir, 'tusx_result.json');
        result_json = jsonencode(result);
        fid = fopen(output_file, 'w');
        fprintf(fid, '%s\n', result_json);
        fclose(fid);
        
        fprintf('TUSX simulation completed successfully.\n');
        fprintf('Result written to: %s\n', output_file);
        exit(0);
        
    catch ME
        % Write error result
        error_result = struct();
        error_result.schema_version = 'tusx-result-v1';
        error_result.job_id = input_data.job_id;
        error_result.status = 'error';
        error_result.error_message = ME.message;
        error_result.error_stack = ME.stack;
        
        output_file = fullfile(run_dir, 'tusx_result.json');
        error_json = jsonencode(error_result);
        fid = fopen(output_file, 'w');
        fprintf(fid, '%s\n', error_json);
        fclose(fid);
        
        fprintf('TUSX simulation failed: %s\n', ME.message);
        exit(1);
    end
end


function initialize_tusx_environment()
    % Add k-Wave and TUSX to MATLAB path
    kwave_path = getenv('KWAVE_PATH');
    tusx_path = getenv('TUSX_PATH');
    
    % Add k-Wave if specified
    if ~isempty(kwave_path)
        if isfolder(kwave_path)
            addpath(kwave_path);
            addpath(fullfile(kwave_path, 'k-Wave'));
            fprintf('Initialized k-Wave path: %s\n', kwave_path);
        else
            warning('k-Wave path not found: %s', kwave_path);
        end
    end
    
    % Add TUSX if specified
    if ~isempty(tusx_path)
        if isfolder(tusx_path)
            addpath(tusx_path);
            addpath(fullfile(tusx_path, 'sim'));
            addpath(fullfile(tusx_path, 'gen'));
            fprintf('Initialized TUSX path: %s\n', tusx_path);
        else
            warning('TUSX path not found: %s', tusx_path);
        end
    end
end


function [simulation_result, metadata] = run_tusx_simulation(input_data)
    % Extract simulation parameters from handoff
    simulation_req = input_data.simulation_request;
    ultrasound_params = simulation_req.ultrasound_parameters;
    probe_pose = simulation_req.probe_pose;
    
    % Extract tissue properties and anatomical model info
    tissue_props = input_data.tissue_properties;
    phantom = input_data.phantom;
    
    % Initialize k-Wave simulation parameters
    frequency_mhz = ultrasound_params.frequency_mhz;
    focal_depth_mm = ultrasound_params.focal_depth_mm;
    gain_db = ultrasound_params.gain_db;
    intensity = ultrasound_params.intensity;
    contact_angle_deg = ultrasound_params.contact_angle_deg;
    coupling_quality = ultrasound_params.coupling_quality;
    
    % PHASE 3: Real k-Wave simulation using TUSX
    fprintf('Starting Phase 3 k-Wave simulation...\n');
    
    % Load synthetic head model from repository data directory
    skull_nifti_path = fullfile(getenv('US_SIM_ROOT'), 'backend', 'data', 'synthetic_head.nii.gz');
    if ~isfile(skull_nifti_path)
        error('Synthetic head model not found: %s', skull_nifti_path);
    end
    
    % Load skull mask
    skull_info = niftiinfo(skull_nifti_path);
    skull_mask = niftiread(skull_nifti_path);

    % Downsample for practical runtime/memory in Phase 3 integration testing.
    skull_mask = skull_mask(1:4:end, 1:4:end, 1:4:end);
    
    % Set up transducer parameters (simplified for initial testing)
    transducer = struct();
    transducer.frequency = frequency_mhz * 1e6;  % Hz
    transducer.elements = 256;  % number of elements
    transducer.width = 0.1e-3;  % element width (m)
    transducer.height = 10e-3;  % element height (m)
    transducer.kerf = 0.05e-3;  % kerf width (m)
    transducer.focus = focal_depth_mm * 1e-3;  % focal distance (m)
    
    % Set up simulation grid based on skull mask
    grid_size = size(skull_mask);
    dx = skull_info.PixelDimensions(1) * 1e-3;  % convert mm to m
    dy = skull_info.PixelDimensions(2) * 1e-3;
    dz = skull_info.PixelDimensions(3) * 1e-3;
    
    % Create k-Wave grid
    kgrid = kWaveGrid(grid_size(1), dx, grid_size(2), dy, grid_size(3), dz);
    
    % Define medium properties based on skull mask
    % 0 = water/CSF, 1 = brain, 2 = skull
    medium.sound_speed = 1500 * ones(grid_size);  % m/s, water
    medium.sound_speed(skull_mask == 1) = 1560;   % brain
    medium.sound_speed(skull_mask == 2) = 2800;   % skull (bone)
    
    medium.density = 1000 * ones(grid_size);      % kg/m³, water
    medium.density(skull_mask == 1) = 1040;       % brain
    medium.density(skull_mask == 2) = 1900;       % skull
    
    medium.alpha_coeff = 0.5 * ones(grid_size);   % dB/(MHz^y cm)
    medium.alpha_power = 1.1;
    
    % Create time array using k-Wave helper (stable dt/CFL handling).
    kgrid.makeTime(medium.sound_speed);
    t_end = kgrid.t_array(end);
    
    % Create source (transducer aperture)
    source.p_mask = zeros(grid_size);
    aperture_center = grid_size(2) / 2;  % center in y
    aperture_width = round(transducer.elements * (transducer.width + transducer.kerf) / dy);
    aperture_start = max(1, aperture_center - aperture_width/2);
    aperture_end = min(grid_size(2), aperture_center + aperture_width/2);
    source.p_mask(:, aperture_start:aperture_end, 1) = 1;
    
    % Create initial pressure distribution (focused wave)
    source.p0 = zeros(grid_size);
    source.p0(source.p_mask == 1) = 1;  % uniform pressure
    
    % Set sensor to record pressure everywhere
    sensor.mask = ones(grid_size);
    sensor.record = {'p'};
    
    % Set simulation options
    input_args = {'PMLSize', 10, 'PMLInside', false, 'PlotPML', false, 'DisplayMask', 'off'};
    
    % Run k-Wave simulation
    fprintf('Running kspaceFirstOrder3D simulation...\n');
    tic;
    sensor_data = kspaceFirstOrder3D(kgrid, medium, source, sensor, input_args{:});
    computation_time = toc;
    fprintf('Simulation completed in %.2f seconds\n', computation_time);
    
    % Extract final pressure field from sensor samples and reshape to grid.
    pressure_samples = sensor_data.p;
    num_points = numel(sensor.mask);
    if size(pressure_samples, 1) == num_points
        last_sample = pressure_samples(:, end);
    elseif size(pressure_samples, 2) == num_points
        last_sample = pressure_samples(end, :)';
    else
        error('Unexpected sensor_data.p shape: %dx%d', size(pressure_samples, 1), size(pressure_samples, 2));
    end
    pressure_field = reshape(last_sample, grid_size);
    
    % Resolve current and future reconstruction artifact paths.
    pressure_file = input_data.artifacts.pressure_field_file;
    receive_channel_raw_file = input_data.artifacts.receive_channel_raw_file;
    receive_channel_data_file = input_data.artifacts.receive_channel_data_file;
    receive_channel_metadata_file = input_data.artifacts.receive_channel_metadata_file;
    reconstruction_metadata_file = input_data.artifacts.reconstruction_metadata_file;

    % Save pressure field for later B-mode processing
    save(pressure_file, 'pressure_field', 'kgrid', 'medium', 'transducer');
    fprintf('Pressure field saved to: %s\n', pressure_file);

    % Extract a first receive aperture from the recorded full-field time series.
    pressure_time_series = sensor_data.p;
    if size(pressure_time_series, 1) ~= num_points
        pressure_time_series = pressure_time_series';
    end

    receive_element_count = min(64, max(8, round((aperture_end - aperture_start + 1) / 2)));
    receive_y_positions = unique(round(linspace(aperture_start, aperture_end, receive_element_count)));
    receive_element_count = length(receive_y_positions);
    receive_x = round(grid_size(1) / 2);
    receive_z = 1;

    receive_linear_indices = zeros(receive_element_count, 1);
    element_positions_mm = zeros(receive_element_count, 3);
    element_normals = zeros(receive_element_count, 3);
    for element_idx = 1:receive_element_count
        receive_y = receive_y_positions(element_idx);
        receive_linear_indices(element_idx) = sub2ind(grid_size, receive_x, receive_y, receive_z);
        element_positions_mm(element_idx, :) = [
            (receive_x - 1) * dx * 1000,
            (receive_y - 1) * dy * 1000,
            (receive_z - 1) * dz * 1000
        ];
        element_normals(element_idx, :) = [0, 0, 1];
    end

    rf_data = zeros(1, receive_element_count, size(pressure_time_series, 2), 'single');
    for element_idx = 1:receive_element_count
        rf_data(1, element_idx, :) = single(pressure_time_series(receive_linear_indices(element_idx), :));
    end
    time_axis_s = double(kgrid.t_array(:));
    tx_event_origin_mm = [
        (receive_x - 1) * dx * 1000,
        ((aperture_start + aperture_end) / 2 - 1) * dy * 1000,
        (receive_z - 1) * dz * 1000
    ];

    save(receive_channel_raw_file, 'rf_data', 'time_axis_s', 'element_positions_mm', 'element_normals', 'tx_event_origin_mm');
    fprintf('Receive channel raw data saved to: %s\n', receive_channel_raw_file);

    receive_channel_metadata = struct();
    receive_channel_metadata.schema_version = 'receive-channel-v1';
    receive_channel_metadata.job_id = input_data.job_id;
    receive_channel_metadata.created_at_utc = char(datetime('now', 'TimeZone', 'UTC', 'Format', 'yyyy-MM-dd''T''HH:mm:ssXXX'));
    receive_channel_metadata.engine = 'tusx';
    receive_channel_metadata.simulation_backend = struct('toolbox', 'k-wave', 'wrapper', 'tusx_matlab_launcher.m', 'resolution', 'phase2-receive-channel');
    receive_channel_metadata.data_layout = struct('rf_data_shape', size(rf_data), 'array_order', {{'tx', 'rx', 'sample'}}, 'dtype', 'single');
    receive_channel_metadata.units = struct('distance', 'mm', 'time', 's', 'sampling_frequency', 'Hz', 'center_frequency', 'Hz', 'sound_speed', 'm/s');
    receive_channel_metadata.probe = struct('probe_id', 'phase2-linear-array-prototype', 'element_count', receive_element_count, 'pitch_mm', dy * 1000, 'kerf_mm', transducer.kerf * 1000, 'element_width_mm', transducer.width * 1000, 'element_height_mm', transducer.height * 1000, 'coordinate_frame', 'simulation_grid_mm');
    receive_channel_metadata.acquisition = struct('transmit_event_count', 1, 'receive_element_count', receive_element_count, 'sample_count', size(rf_data, 3), 'sampling_frequency_hz', 1 / (kgrid.t_array(2) - kgrid.t_array(1)), 'center_frequency_hz', transducer.frequency, 'sound_speed_m_per_s', 1540, 'tx_focus_mm', focal_depth_mm, 'tx_steering_deg', 0, 'recorded_quantity', 'pressure_time_series');
    receive_channel_metadata.coordinate_system = struct('frame', 'simulation_grid_mm', 'handedness', 'right-handed', 'axes', struct('x', 'grid-x', 'y', 'grid-y', 'z', 'grid-z'));
    receive_channel_metadata.source_artifacts = struct('tusx_input_path', input_file, 'run_directory', run_dir, 'pressure_field_path', pressure_file, 'receive_channel_raw_path', receive_channel_raw_file, 'receive_channel_data_path', receive_channel_data_file);
    fid = fopen(receive_channel_metadata_file, 'w');
    fprintf(fid, '%s\n', jsonencode(receive_channel_metadata));
    fclose(fid);
    fprintf('Receive channel metadata saved to: %s\n', receive_channel_metadata_file);
    
    % Placeholder results for now (will be replaced with B-mode processing)
    attenuation = mean(medium.alpha_coeff(:)) * frequency_mhz * 0.1;  % rough estimate
    reflection = 0.3;  % placeholder
    latency_ms = 1000 * t_end;  % rough estimate
    
    % Path segments (simplified)
    path_segments = struct();
    path_segments(1).structure_id = 'skull';
    path_segments(1).tissue_id = 'skull';
    path_segments(1).length_mm = 10;
    path_segments(1).attenuation_contribution = attenuation * 0.5;
    
    path_segments(2).structure_id = 'brain';
    path_segments(2).tissue_id = 'brain';
    path_segments(2).length_mm = focal_depth_mm;
    path_segments(2).attenuation_contribution = attenuation * 0.5;
    
    % Region hits
    region_hits = struct();
    region_hits(1).structure_id = 'skull';
    region_hits(1).label = 'Skull';
    region_hits(1).hit_strength = 0.4 * intensity;
    
    region_hits(2).structure_id = 'brain';
    region_hits(2).label = 'Brain Tissue';
    region_hits(2).hit_strength = 0.6 * intensity;
    
    % Build result structure
    simulation_result = struct();
    simulation_result.grayscale_image_url = '/api/simulation/bmode-placeholder';  % Will be real B-mode later
    
    summary = struct();
    summary.attenuation_estimate = round(attenuation, 3);
    summary.focal_region_depth_mm = focal_depth_mm;
    summary.estimated_latency_ms = round(latency_ms);
    summary.reflection_estimate = round(reflection, 3);
    summary.frequency_mhz = frequency_mhz;
    summary.contact_angle_deg = contact_angle_deg;
    summary.coupling_quality = coupling_quality;
    simulation_result.summary = summary;
    
    simulation_result.path_segments = path_segments;
    simulation_result.region_hits = region_hits;
    
    % Metadata about the simulation run
    metadata = struct();
    metadata.engine = 'k-wave';
    metadata.physics_model = 'Full acoustic wave propagation';
    metadata.resolution = 'Phase 3 (real k-Wave)';
    metadata.computation_time_seconds = computation_time;
    metadata.pressure_field_file = pressure_file;
    metadata.receive_channel_raw_file = receive_channel_raw_file;
    metadata.receive_channel_data_file = receive_channel_data_file;
    metadata.receive_channel_metadata_file = receive_channel_metadata_file;
    metadata.reconstruction_metadata_file = reconstruction_metadata_file;
    metadata.receive_channel_capture = 'available';
    metadata.grid_size = grid_size;
    metadata.voxel_size_mm = [dx*1000, dy*1000, dz*1000];
    metadata.notes = 'Real k-Wave simulation completed, B-mode processing pending. Receive-channel artifact paths reserved for Phase 2.';
end
