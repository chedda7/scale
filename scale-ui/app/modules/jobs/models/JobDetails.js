(function () {
    'use strict';

    angular.module('scaleApp').factory('JobDetails', function (scaleConfig, JobType, JobExecution, Product, JobDetailInputData, JobDetailOutputData, Recipe, JobDetailEvent, scaleService) {
        var JobDetails = function (id, job_type, job_type_rev, event, error, status,
                                   priority, num_exes, timeout, max_tries, cpus_required, mem_required,
                                   disk_in_required, disk_out_required, created, queued, started, ended,
                                   last_status_change, last_modified, data, results, recipes, job_exes,
                                   inputs, outputs, is_superseded, root_superseded_job, superseded_job,
                                   superseded_by_job, superseded) {
            this.id = id;
            this.job_type = JobType.transformer(job_type);
            this.job_type_rev = job_type_rev;
            this.event = JobDetailEvent.transformer(event);
            this.error = error;
            this.status = status;
            this.priority = priority;
            this.num_exes = num_exes;
            this.timeout = timeout;
            this.max_tries = max_tries;
            this.cpus_required = cpus_required;
            this.mem_required = mem_required;
            this.disk_in_required = disk_in_required;
            this.disk_out_required = disk_out_required;
            this.created = created;
            this.created_formatted = moment.utc(created).format(scaleConfig.dateFormats.day_second_utc);
            this.queued = queued;
            this.queued_formatted = moment.utc(queued).format(scaleConfig.dateFormats.day_second_utc);
            this.started = started;
            this.started_formatted = moment.utc(started).format(scaleConfig.dateFormats.day_second_utc);
            this.ended = ended;
            this.ended_formatted = moment.utc(ended).format(scaleConfig.dateFormats.day_second_utc);
            this.last_status_change = last_status_change;
            this.last_modified = last_modified;
            this.data = data ? {
                    input_data: JobDetailInputData.transformer(data.input_data),
                    version: data.version,
                    output_data: JobDetailOutputData.transformer(data.output_data)
                } :
                null;
            this.results = results ? {
                    output_data: JobDetailOutputData.transformer(results.output_data),
                    version: results.version
                } :
                null;
            this.recipes = _.sortBy(Recipe.transformer(recipes), ['created']).reverse();
            this.job_exes = JobExecution.transformer(job_exes);
            this.inputs = inputs;
            this.outputs = outputs;
            this.is_superseded = is_superseded;
            this.root_superseded_job = root_superseded_job;
            this.superseded_job = superseded_job;
            this.superseded_by_job = superseded_by_job;
            this.superseded = superseded;
            this.superseded_formatted = moment.utc(superseded).format(scaleConfig.dateFormats.day_second_utc);;

        };

        // public methods
        JobDetails.prototype = {
            getDuration: function () {
                var start = this.started,
                    end = this.ended ? this.ended : moment.utc().toISOString();

                return scaleService.calculateDuration(start, end);
            },
            getLatestExecution: function(){
                if (this.num_exes > 0 ) {
                    return this.job_exes[0];
                }
                return null;
            },
            getStatusClass: function(){
                // if(this.status === 'COMPLETED'){
                //     return 'label-success';
                // }
                // else if( this.status === 'FAILED'){
                //     return 'label-default';//    return 'label-danger';
                // }
                // else{
                //     return 'label-default';
                // }
                return this.status.toLowerCase();
            }
        };

        // static methods, assigned to class
        JobDetails.build = function (data) {
            if (data) {
                return new JobDetails(
                    data.id,
                    data.job_type,
                    data.job_type_rev,
                    data.event,
                    data.error,
                    data.status,
                    data.priority,
                    data.num_exes,
                    data.timeout,
                    data.max_tries,
                    data.cpus_required,
                    data.mem_required,
                    data.disk_in_required,
                    data.disk_out_required,
                    data.created,
                    data.queued,
                    data.started,
                    data.ended,
                    data.last_status_change,
                    data.last_modified,
                    data.data,
                    data.results,
                    data.recipes,
                    data.job_exes,
                    data.inputs,
                    data.outputs,
                    data.is_superseded,
                    data.root_superseded_job,
                    data.superseded_job,
                    data.superseded_by_job,
                    data.superseded
                );
            }
            return new JobDetails();
        };

        JobDetails.transformer = function (data) {
            if (angular.isArray(data)) {
                return data
                    .map(JobDetails.build)
                    .filter(Boolean);
            }
            return JobDetails.build(data);
        };

        return JobDetails;
    });
})();
