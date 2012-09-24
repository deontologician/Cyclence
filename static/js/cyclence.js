function TaskCtrl($scope, $http) {
    $http.get('/api/tasks').success(function(data) {
        $scope.tasks = data.tasks;
    });
}
