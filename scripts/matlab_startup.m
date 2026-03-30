% MATLAB startup script for TUSX + k-Wave integration
% This file should be placed in ~/MATLAB/startup.m or ~/.matlab/R2025b/startup.m
% It will run automatically when MATLAB starts

% Add k-Wave to path
kwave_path = '/mnt/c/Users/rakxa/Desktop/ucl-bug-k-wave-1.4.1.0';
if isfolder(kwave_path)
    addpath(kwave_path);
    addpath(fullfile(kwave_path, 'k-Wave'));
    disp(['Added k-Wave to path: ' kwave_path]);
end

% Add TUSX to path
tusx_paths = {
    '/home/aridgg/us-sim/tusx',
    '/home/aridgg/us-sim/tusx/sim',
    '/home/aridgg/us-sim/tusx/gen',
};

for i = 1:length(tusx_paths)
    path_str = tusx_paths{i};
    if isfolder(path_str)
        addpath(path_str);
        disp(['Added TUSX path: ' path_str]);
    end
end

% Verify essential toolboxes are available
essentials = {'Signal Processing Toolbox', 'Image Processing Toolbox'};
v = ver;
installed_toolboxes = {v.Name};

missing = {};
for i = 1:length(essentials)
    if ~any(strcmp(installed_toolboxes, essentials{i}))
        missing = [missing; essentials(i)];
    end
end

if ~isempty(missing)
    warning('Missing toolboxes: %s', strjoin(missing, ', '));
end

% Save the path for future sessions
savepath;
disp('TUSX + k-Wave environment initialized');
