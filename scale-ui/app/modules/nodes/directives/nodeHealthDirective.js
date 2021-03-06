(function (){
    'use strict';

    angular.module('scaleApp').controller('aisNodeHealthController', function ($rootScope, $scope) {
        var vm = this;

        vm.nodes = [];
        vm.groupedNodes = [];
        vm.totalNodes = 0;

        var getNodeStatus = function () {
            vm.totalNodes = vm.nodes.length;
            if (vm.totalNodes > 0) {
                vm.groupedNodes = _.pairs(_.groupBy(vm.nodes, 'state.title'));

                var donutData = [];

                _.forEach(vm.groupedNodes, function (group) {
                    donutData.push({
                        status: group[0],
                        count: group[1].length
                    });
                });

                vm.nodeHealth = donutData;
            } else {
                vm.nodeHealth = [];
            }
        };

        $scope.$watch('data', function (newValue) {
            if (newValue) {
                vm.nodes = newValue;
                vm.totalNodes = newValue.length;
                getNodeStatus();
            }
        });
    }).directive('aisNodeHealth', function(){
        /**
         * Usage: <ais-node-health />
         **/
         return {
             controller: 'aisNodeHealthController',
             controllerAs: 'vm',
             templateUrl: 'modules/nodes/directives/nodeHealthTemplate.html',
             restrict: 'E',
             scope: {
                 data: '=',
                 showDescription: '=',
                 loading: '=',
                 nodeType: '@'
             }
         };
    });
})();
