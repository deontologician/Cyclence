
function MainCtrl($scope) {
    $scope.gravatar_border = "0,100%,50%";
}

function TaskCtrl($scope, $http) {
    $http.get('/api/tasks').success(function(data) {
        $scope.tasks = data.tasks;
        $scope.current_task = null;
        $scope.gravatar_border = data.tasks[0].hsl;
        $scope.complete = function(task) {
            $scope.current_task = task;
        }
    });
}
angular.module('cyclence', ['ui']);
