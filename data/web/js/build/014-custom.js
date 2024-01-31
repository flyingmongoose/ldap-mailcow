$( document ).ready(function() {
  // disable quota, username,custom attrs inputs
    $("#collapse-tab-medit > form > div:nth-child(5) > div").addClass("custom_disabled_div");
    $("#collapse-tab-medit > form > div:nth-child(7) > div").addClass("custom_disabled_div");
    $("#collapse-tab-mattr > form tr").addClass("custom_disabled_div");
    $(".custom_disabled_div input[name='name']").attr('tabindex', '-1');
    $(".custom_disabled_div input[name='quota']").attr('tabindex', '-1');
    $(".custom_disabled_div input[data-id='mbox_attr']").attr('tabindex', '-1');
});

