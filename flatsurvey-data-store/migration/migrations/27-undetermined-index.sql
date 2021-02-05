CREATE INDEX undetermined_interval_exchange_transformation_intervals ON flatsurvey.undetermined_interval_exchange_transformation USING gin ((data -> 'intervals'));
CREATE INDEX undetermined_interval_exchange_transformation_degree ON flatsurvey.undetermined_interval_exchange_transformation USING gin ((data -> 'degree'));

