function FeedbackBlock(runtime, element, data) {

  // When the user asks to save, read the form data and send it via AJAX
  $(element).find(".save-button").on("click", function() {
    let handlerUrl = runtime.handlerUrl(element, "studio_submit");
    let form_data = {
      "likert": $(element).find("input[name=likert]").val(),
      "freeform": $(element).find("input[name=freeform]").val(),
      "placeholder": $(element).find("input[name=placeholder]").val(),
      "icon_set": $(element).find("select[name=icon_set]").val(),
      "display_name": $(element).find("input[name=display_name]").val(),
      "scale_text": {},
      "enable_zero_grade": $(element).find("select[name=zero-grade]").val(),
      "zero_likert": $(element).find("input[name=zero_likert]").val(),
      "enable-text-area-answer": $(element).find("select[name=enable-text-area-answer]").val(),
    };

    $( ".likert-item" ).each(function() {
      form_data["scale_text"][$( this ).attr("name").replace("likert-", "")] = $( this ).val();
    });

    runtime.notify("save", {state: "start"});
    $.post(handlerUrl, JSON.stringify(form_data)).done(function(response) {
        runtime.notify("save", {state: "end"});
    });
  });

  $(element).find("#zero-grade").change(function() {
    if ($( this ).val() === "true") {
      $(element).find(".enable-zero-grade").removeAttr("hidden");
    } else {
      $(element).find(".enable-zero-grade").attr("hidden", true);
    }
  });

  $(element).find("#enable-text-area-answer").change(function() {
    let freeformClass = ".freeform";
    let freeformPlaceholderClass = ".freeform-placeholder";

    if ($( this ).val() === "true") {
      $(element).find(freeformClass).removeAttr("hidden");
      $(element).find(freeformPlaceholderClass).removeAttr("hidden");
    } else {
      $(element).find(freeformClass).attr("hidden", true);
      $(element).find(freeformPlaceholderClass).attr("hidden", true);
    }
  });

  // When the user hits cancel, use Studio"s proprietary notify()
  // extension
  $(element).find(".cancel-button").bind("click", function() {
    runtime.notify("cancel", {});
  });

  // Select the right icon set in the dropdown
  $(element).find("select[name=icon_set]").val(data["icon_set"]);
}
