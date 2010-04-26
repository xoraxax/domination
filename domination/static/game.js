handle_page_refresh = function () {
  var seqno = initial_seqno;
  var check_and_update = function() {
    $.getJSON($SCRIPT_ROOT + '/game/get_seqno/' + game_name, {seqno: seqno}, function(data) {
      document.location = document.location;
      window.setTimeout(check_and_update, 100);
    });
  };
  window.setTimeout(check_and_update, 100);
}
