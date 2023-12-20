$( document ).ready(function() {
  // disable quota and username inputs
    $("#collapse-tab-medit > form > div:nth-child(5) > div").addClass("custom_disabled_div");
    $("#collapse-tab-medit > form > div:nth-child(7) > div").addClass("custom_disabled_div");
    $(".custom_disabled_div input[name='name']").attr('tabindex', '-1');
    $(".custom_disabled_div input[name='quota']").attr('tabindex', '-1');
});
