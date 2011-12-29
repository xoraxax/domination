do_page_refresh = true;
handle_page_refresh = function () {
  var seqno = initial_seqno;
  var check_and_update = function() {
    $.getJSON($SCRIPT_ROOT + '/game/check_seqno/' + game_name, {seqno: seqno}, function(data) {
      if (!(data === null) && do_page_refresh) {
        document.location = document.location;
      }
    });
  };
  window.setTimeout(check_and_update, 100);
};

function your_turn_reminder() {
    var intervalId = setInterval(function() {
        $('body').css('background-color', '#ffffdd');
    }, 2000);
    var oldTitle = document.title;
    var msg = "Your turn!";
    var timeoutId = setInterval(function() {
        document.title = document.title == msg ? oldTitle : msg;
    }, 1000);
    window.onmousemove = function() {
        $('body').css('background-color', 'transparent');
        clearInterval(intervalId);
        clearInterval(timeoutId);
        document.title = oldTitle;
        window.onmousemove = null;
    };
}

_toggle_supply_lock = false;

function show_pile(selector, title) {
  do_page_refresh = false;
  $(selector).dialog({ modal: true, width: 700, title: title,
      close: function(event, ui) {
        do_page_refresh = true;
        handle_page_refresh();
      }
  });
}
