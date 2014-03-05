





// BRAVE Forums

(function($) {
    
    var Forums = function() {
        this.running = false;
        this.bound = false;
        this.flash = new $.Flash('#notices', 5000);
    }
    
    Forums.extend = function(mapping) {
        $.extend(Forums.prototype, mapping);
    }
    
    
    Forums.extend({
        
        on: function(event, handler) {
            $(this).on(event, handler);
        },
        
        ready: function() {
            
            $(this).trigger('bind', [true]);
            
            this.running = true;
            
        },
        
        bind: function(initial) {
            if ( initial ) {
                // Prevent access of disabled elements.  This must be the first handler, thus always bind events to body.
                $('body').on('click.disabled', '.disabled', function(e) {
                    e.preventDefault();
                });
                
                // Disable moving-to-top for pure hash links.
                $('body').on('click.fragment', 'a[href="#"][data-top!=true]', function(e){ e.preventDefault(); });
                
                // Automatically destroy all modal dialogs.  Keep the DOM clean.
                $('body').on('hidden.modal', '#modal', function(){ $('#modal').remove(); });
            }
            
            for ( var selector in Forums.events ) {
                Forums.events[selector].call($(selector));
            }
        },
        
        confirm: function(title, content, success, callback) {
            if ( ! success.hasOwnProperty('label') )
                success = {label: success, kind: 'btn-primary'};
            
            $('<div id="modal" class="modal hide fade">' +
                '<div class="modal-header">' +
                    '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                    '<h3>' + title + '</h3>' +
                '</div>' +
                '<div class="modal-body">' + content + '</div>' +
                '<div class="modal-footer">' +
                    '<a href="#" class="btn" data-dismiss="modal">Cancel</a>' +
                    '<a href="#" id="modal-confirm" class="btn ' + success.kind + '">' + success.label + '</a>' +
                '</div>' +
            '</div>').appendTo('body');
            
            $('#modal-confirm').on('click', function(e) {
                if ( callback() ) return;
                e.preventDefault();
                $('#modal').modal('hide')
            });
            
            $('#modal').modal();
        },
        
    });
    
    Forums.events = {
        '[rel="tooltip"],[data-rel="tooltip"]': function() { this.tooltip({delay: 200}); },
        '[rel="popover"],[data-rel="popover"]': function() { this.popover(); },
        'tr:first-child': function() { this.addClass('first'); },
        // '': function() { },
    };
    
    
    $.forums = new Forums();
    
    
    // Handle theme changes.
    $.forums.on('bind', function(first) {
        if ( !first ) return;
        
        $('a[data-theme]').click(function(e){
            e.preventDefault();
            
            var self = $(this),
                selection = self.data('theme');
            
            switch ( selection ) {
                case 'default':
                    $('link#theme').remove();
                    break;
                
                case 'custom':
                    break;
                
                default:
                    $('link#theme').remove();
                    $('<link href="/css/theme-' + selection + '.css" rel="stylesheet" id="theme">').appendTo('head');
            }
            
            $('.nav.alice a[data-theme] i').removeClass('fa-dot-circle-o').addClass('fa-circle-o');
            $('.nav.alice a[data-theme="' + selection + '"] i').removeClass('fa-circle-o').addClass('fa-dot-circle-o');
            
            $.post('/theme', {theme: selection});
        });
    });
    
    
    // TODO: Move infiniscrolling here.
    
    
    // Startup
    $($.proxy($.forums.ready, $.forums));
    
})(jQuery);
