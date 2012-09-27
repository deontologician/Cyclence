function MainCtrl($scope) {
    $scope.gravatar_border = "0,100%,50%";
}

function TaskCtrl($scope, $http) {
    $http.get('/api/tasks').success(function(data) {
        $scope.tasks = data.tasks;
        $scope.gravatar_border = data.tasks[0].hsl;
    });
}
