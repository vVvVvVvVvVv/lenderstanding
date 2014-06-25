/* Your fancy javascript */
$(document).ready(function() {
    $('div').click(function() {
        $('div').fadeTo('fast',1);
    });    
    $('div').mouseleave(function() {
        $('div').fadeTo('fast',0.5);
    });
});

