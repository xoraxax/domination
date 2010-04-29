handle_page_refresh = function () {
  var seqno = initial_seqno;
  var check_and_update = function() {
    $.getJSON($SCRIPT_ROOT + '/game/check_seqno/' + game_name, {seqno: seqno}, function(data) {
      if (!(data === null)) {
        document.location = document.location;
        window.setTimeout(check_and_update, 100);
      }
    });
  };
  window.setTimeout(check_and_update, 100);
};

function your_turn_reminder() {
    var oldTitle = document.title;
    var msg = "Your turn!";
    var timeoutId = setInterval(function() {
        document.title = document.title == msg ? ' ' : msg;
    }, 1000);
    window.onmousemove = function() {
        clearInterval(timeoutId);
        document.title = oldTitle;
        window.onmousemove = null;
    };
}

_toggle_supply_lock = false;

function toggle_supply() {
  if (!_toggle_supply_lock) {
    this._toggle_supply_lock = true;
    $('div#supplycards').slideToggle(500, function() {
      _toggle_supply_lock = false;
    });
  }
}
