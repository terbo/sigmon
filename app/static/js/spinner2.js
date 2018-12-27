$(function() {
  var action;
  $(".number-spinner button").mousedown(function () {
    btn = $(this);
    input = btn.closest('.number-spinner').find('input');
    btn.closest('.number-spinner').find('button').prop("disabled", false);

    if (btn.attr('data-dir') == 'up') {
      action = setInterval(function(){
        if ( input.attr('max') == undefined || parseInt(input.val()) < parseInt(input.attr('max')) ) {
          input.val(parseInt(input.val())+1);
        }else{
          btn.prop("disabled", true);
          clearInterval(action);
        }
      }, 50);
   } else {
      action = setInterval(function(){
        if ( input.attr('min') == undefined || parseInt(input.val()) > parseInt(input.attr('min')) ) {
          input.val(parseInt(input.val())-1);
        }else{
          btn.prop("disabled", true);
          clearInterval(action);
        }
      }, 50);
   }
  }).mouseup(function(){
    clearInterval(action);
  });
});
