handle_page_refresh = function () {
  var seqno = initial_seqno;
  var check_and_update = function() {
    $.getJSON($SCRIPT_ROOT + '/game/get_seqno/' + game_name, {seqno: seqno}, function(data) {
      new_seqno = data.result;
      if (new_seqno != seqno) {
        seqno = new_seqno;
        document.location = document.location;
      }
      window.setTimeout(check_and_update, 500);
    });
  };
  window.setTimeout(check_and_update, 500);
}
