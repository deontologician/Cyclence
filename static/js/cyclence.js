angular.module('Cyclence', ['ngResource', 'ui']);

function MainCtrl($scope) {
    $scope.gravatar_border = "0,100%,50%";
}

function today(){
    d = new Date()
    return '' + d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
}


function TaskCtrl($scope, $resource) {
    
    $scope.Tasks = $resource('/api/tasks');
    $scope.Completion = $resource('/api/tasks/:task_id/completions/:completed_on',
                            {task_id: '@task_id', completed_on: '@completed_on'},
                                  {complete : 
                                   {method: 'PUT'}
                                  });

    
    $scope.tasks = $scope.Tasks.query(function () {
        $scope.current_task = null;
        $scope.complete = function(task) {
            $scope.current_task = task;
            $scope.gravatar_border = task.hsl;
            $scope.Completion.complete({task_id: task.id,
                                        completed_on: today()});
        }
    });
}


