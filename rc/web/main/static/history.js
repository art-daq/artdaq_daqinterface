function update_fetcher(url, period_arg, success_fn, datatype) {
    var fetch_interval;
    var period = period_arg || 1000; // msec
    function interval_fn() {
        clearInterval(fetch_interval);
        $.ajax({url: url,
                dataType: datatype || "json"})
            .done(function(data) {
                      success_fn(data);
                      fetch_interval = setInterval(interval_fn, period);
                  })
            .fail(function(data) {
                      console.log("FAIL", data);
                      fetch_interval = setInterval(interval_fn, period);
                  });
    }
    fetch_interval = setInterval(interval_fn, period);
}




update_fetcher("/lbnerc/control/monilong/", 3000, 
                function(data) {
                    $("#moni-values-long").html(data);
                }, "html");


