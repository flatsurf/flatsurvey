CREATE INDEX flow_decomposition_undetermined ON flatsurvey.flow_decomposition USING gin ((data -> 'undetermined'));
CREATE INDEX flow_decomposition_minimal ON flatsurvey.flow_decomposition USING gin ((data -> 'minimal'));
CREATE INDEX flow_decomposition_cylinders ON flatsurvey.flow_decomposition USING gin ((data -> 'cylinders'));
