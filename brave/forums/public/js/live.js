//
// A jQuery extension to handle Nginx HTTP Push Module (NHPM) channel polling.
//


// Primary constructor.
// var channel = new Channel({...});

var Channel = function(options) {
    console.log('Channel.init');
    this.settings = jQuery.extend({}, Channel.defaults, options);
    
    this.alive = false;  // are we currently polling?
    this.throttle = 0;  // the throttle multiplicand (determining delay between requests)
    this.failures = 0;  // number of consecutive failures [TODO]
    this.xhr = null;  // the currently executing (or last executed) XHR request
    this.last = null;  // the date/time of the last update through the stream [TODO]
    
    return this;
};


Channel.defaults = {
    path: '/listen',  // we default to the global per-user channel for convienence
    
    accept: 'text/plain, application/json, text/html',
    type: 'json',  // usually we get json back, though sometimes we might simply stream HTML
    
    // these will need to be tweaked to balance performance and load
    
    idle: 3600,  // stop trying after an hour of no activity  [TODO]
    retry: 5,  // initially retry every 5 seconds, but this increases each try up to the maximum
    maximum: 60,  // don't wait longer than a minute betwen attempts to poll
    timeout: 600,  // 10 minutes, if we can get away with it
    failures: 5,  // maximum number of consecutive errors before giving up
};


// Trigger event capture for this channel.

Channel.prototype.listen = function() {
    console.log('Channel.listen');
    
    this.alive = true;
    this.throttle = 0;
    this.failures = 0;
    
    this.trigger();
};


Channel.prototype.deafen = function() {
    console.log('Channel.deafen');
    
    this.alive = false;

    if ( this.timeout ) clearTimeout(this.timeout);
    if ( this.xhr !== null ) this.xhr.abort();
}


Channel.prototype.trigger = function() {
    var delay = Math.min(this.settings.retry * this.throttle * 1000, this.settings.maximum * 1000);
    
    console.log('Channel.trigger', delay);
    
    this.timeout = setTimeout($.proxy(this, 'request'), delay);
};


Channel.prototype.request = function() {
    console.log('Channel.request', this.settings.path);
    
    this.xhr = $.ajax(this.settings.path, {
            global: false,
            accept: this.settings.accept,
            dataType: this.settings.type,
            cache: true,
            ifModified: true,
            context: this,
            timeout: this.settings.timeout * 1000,
        });
    
    this.xhr.done(this.packet);
    this.xhr.fail(this.failure);
    this.xhr.always(this.cleanup);
};


Channel.prototype.packet = function(data, status, xhr) {
    console.log('Channel.packet', data);
    $(this).trigger('channel.message', [data, xhr]);
};


Channel.prototype.failure = function(xhr, status, error) {
    // status = "timeout", "error", "abort", and "parsererror"
    // error = HTTP status string
    
    console.log('Channel.failure', status, error);
    
    return $.proxy(this, 'handle_' + status)(xhr, error);
};


Channel.prototype.cleanup = function(xhr, status) {
    // Called after all other handlers have been executed.
    // We determine if we re-trigger this monster.
    
    if ( ! this.alive ) {
        console.log('Channel.cleanup', false);
        
        $(this).trigger('channel.shutdown');
        return;
    }
    
    console.log('Channel.cleanup', true);

    this.trigger();
};


Channel.prototype.handle_timeout = function(xhr, error) {
    console.log('Channel.timeout.handler');
    this.throttle++;
    $(this).trigger('channel.timeout', [xhr]);
};


Channel.prototype.handle_error = function(xhr, error) {
    console.log('Channel.error.handler');
    this.throttle++;
    $(this).trigger('channel.error', [xhr, error]);
};


Channel.prototype.handle_abort = function(xhr, error) {
    console.log('Channel.abort.handler');
    this.alive = false;
    $(this).trigger('channel.abort', [xhr]);
};


Channel.prototype.handle_parsererror = function(xhr, error) {
    console.log('Channel.malformed.handler');
    $(this).trigger('channel.malformed', [xhr, xhr.responseText]);
};






var Notifications = function(path) {
    console.log('Notifications.init');

    this.channel = new Channel({
            path: path,
        });
    
    $(this.channel).on({
            "channel.message": $.proxy(this, 'on_message'),
            "channel.shutdown": $.proxy(this, 'stopped'),
            "channel.error": $.proxy(this, 'trouble'),
            "channel.malformed": $.proxy(this, 'trouble'),
        });
    
    return this;
};


Notifications.prototype.start = function(e) {
    console.log('Notifications.start');
    this.channel.listen();
    $(this).trigger('starting');
};


Notifications.prototype.stop = function(e) {
    console.log('Notifications.stop');
    this.channel.deafen();
    $(this).trigger('stopping');
};


Notifications.prototype.stopped = function(e) {
    console.log('Notifications.stopped');
    $(this).trigger('stopped');
};


Notifications.prototype.trouble = function(xhr) {
    console.log('Notifications.trouble');
    $(this).trigger('trouble');
};


Notifications.prototype.on_message = function(e, data, xhr) {
    console.log('Notifications.message', data.handler, data.payload);
    $(this).trigger('notice.' + data.handler, [data.payload]);
};





var Thread = function() {
    console.log('Thread.init');

    this.channel = new Notifications($('body').data('thread-endpoint'));
    
    $(this.channel).on({
            "notice.locked": $.proxy(this, 'locked'),
            "notice.unlocked": $.proxy(this, 'unlocked'),
            "notice.sticky": $.proxy(this, 'sticky'),
            "notice.unsticky": $.proxy(this, 'unsticky'),
            "notice.hidden": $.proxy(this, 'hidden'),
            "notice.visible": $.proxy(this, 'visible'),
            
            "notice.comment": $.proxy(this, 'commented'),
            "notice.refresh": $.proxy(this, 'refreshed'),
            "notice.remove": $.proxy(this, 'removed'),
            "notice.stop": $.proxy(this, 'stop'),
            
            "starting": $.proxy(this, 'starting'),
            "stopping": $.proxy(this, 'starting'),
            "stopped": $.proxy(this, 'starting'),
            "trouble": $.proxy(this, 'starting'),
        });
    
    $('#toggle-live').on('click', $.proxy(this, 'toggle'));
    
    return this;
};


Thread.prototype.toggle = function(e) {
    var pill = $('.connection-state');
    console.log("Thread.toggle", pill.hasClass('active') ? 'stop' : 'start');
    
    if ( pill.hasClass('active') ) {
        this.channel.stop();
    } else {
        this.channel.start();
    }
};


Thread.prototype.stop = function() {
    this.channel.stop();
}


Thread.prototype.setState = function(level, state) {
    console.log("Thread.setState", level, state);
    $('.connection-state').removeClass('active disabled').addClass(level);
    $('.connection-state i').addClass('hidden').filter('.' + state).removeClass('hidden');
};




Thread.prototype.locked = function(data) {
    console.log("Thread.locked");
};

Thread.prototype.unlocked = function(data) {
    console.log("Thread.unlocked");
};

Thread.prototype.sticky = function(data) {
    console.log("Thread.sticky");
};

Thread.prototype.unsticky = function(data) {
    console.log("Thread.unsticky");
};

Thread.prototype.hidden = function(data) {
    console.log("Thread.hidden");
};


Thread.prototype.visible = function(data) {
    console.log("Thread.visible");
};


Thread.prototype.commented = function(e, identifier) {
    console.log("Thread.commented", identifier);

    if ( $('#' + identifier).length ) return;
    
    $.get(window.location.pathname + '/' + identifier + '.html', function(result) {
        // This is really where de-dupe is most critical.
        if ( $('#' + identifier).length ) return;
        $(result).insertAfter('.comment:last');
        $('time.relative').timeago();
    });
};

Thread.prototype.refreshed = function(e, identifier) {
    console.log("Thread.refresh", identifier);

    if ( ! $('#' + identifier).length ) return;
    
    $.get(window.location.pathname + '/' + identifier + '.html', function(result) {
        $('#' + identifier).replaceWith(result);
        $('time.relative').timeago();
    });
};

Thread.prototype.removed = function(e, identifier) {
    console.log("Thread.remove", identifier);

    if ( ! $('#' + identifier).length ) return;
    $('#' + identifier).remove();
};




Thread.prototype.starting = function(e) {
    console.log("Thread.starting");
    this.setState('active', 'live');
};


Thread.prototype.stopping = function(e) {
    console.log("Thread.stopping");
    this.setState('', 'live');
};


Thread.prototype.stopped = function(e) {
    console.log("Thread.stopped");
    this.setState('', 'disconnected');
};


Thread.prototype.trouble = function(xhr) {
    console.log("Thread.trouble");
    this.setState('', 'live')
};
