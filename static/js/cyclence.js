Cycl = Cycl || {};

Cycl.today = function(){
    var d = new Date()
    return '' + d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate();
}
