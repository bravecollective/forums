//
// A jQuery extension to handle Nginx HTTP Push Module (NHPM) channel polling.
//


// Primary constructor.
// var channel = new Channel({...});

var Channel = function(options) {
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
    
    headers: {},
    
    // these will need to be tweaked to balance performance and load
    
    idle: 3600,  // stop trying after an hour of no activity  [TODO]
    retry: 5,  // initially retry every 5 seconds, but this increases each try up to the maximum
    maximum; 60,  // don't wait longer than a minute betwen attempts to poll
    timeout: 600,  // 10 minutes, if we can get away with it
    failures: 5,  // maximum number of consecutive errors before giving up
};


// Trigger event capture for this channel.

Channel.prototype.listen = function() {
    this.alive = true;
    this.throttle = 0;
    this.failures = 0;
    
    this.trigger();
};


Channel.prototype.deafen = function() {
    this.alive = false;
    if ( this.timeout ) clearTimeout(this.timeout);
    if ( this.xhr !== null ) this.xhr.abort();
}


Channel.prototype.trigger = function() {
    var delay = Math.min(this.settings.retry * this.throttle * 1000, this.settings.maximum * 1000);
    this.timeout = setTimeout($.proxy(this, 'request'), delay);
};


Channel.prototype.request = function() {
    this.xhr = $.ajax(this.settings.path, {
            global: false,
            accept: this.settings.accept,
            dataType: this.settings.type,
            cache: true,
            ifModified: true,
            headers: this.settings.headers,
            context: this,
            timeout: this.settings.timeout * 1000,
        });
    
    this.xhr.done(this.packet);
    this.xhr.fail(this.failure);
    this.xhr.always(this.cleanup);
};


Channel.prototype.packet = function(e, data, status, xhr) {
    $(this).trigger('channel.message', [data, xhr]);
};


Channel.prototype.failure = function(e, xhr, status, error) {
    // status = "timeout", "error", "abort", and "parsererror"
    // error = HTTP status string
    
    return $.proxy(this, 'handle_' + status)(e, xhr, error);
};


Channel.prototype.cleanup = function(e, xhr, status) {
    // Called after all other handlers have been executed.
    // We determine if we re-trigger this monster.
    
    if ( ! this.alive ) {
        $(this).trigger('channel.shutdown');
        return;
    }
    
    this.trigger();
};


Channel.prototype.handle_timeout = function(e, xhr, error) {
    this.throttle++;
    $(this).trigger('channel.timeout', [xhr]);
};


Channel.prototype.handle_error = function(e, xhr, error) {
    this.throttle++;
    $(this).trigger('channel.error', [xhr, error]);
};


Channel.prototype.handle_abort = function(e, xhr, error) {
    this.alive = false;
    $(this).trigger('channel.abort', [xhr]);
};


Channel.prototype.handle_parsererror = function(e, xhr, error) {
    $(this).trigger('channel.malformed', [xhr, xhr.responseText]);
};






var Notifications = function(path) {
    this.channel = new Channel({
            path: $.extend({}, Notifications.defaults, {path: path}).path,  // I've been up for three days.
        });
    
    $(this.channel).on({
            "channel.packet": $.proxy(this, 'on_message'),
            "channel.shutdown": $.proxy(this, 'stopped'),
            "channel.abort": $.proxy(this, 'stopped'),
            "channel.error": $.proxy(this, 'trouble'),
            "channel.malformed": $.proxy(this, 'trouble'),
        });
    
    return this;
};


Notifications.defaults = {
    path: '/listen',  // we default to the global per-user channel for convienence
};


Notifications.prototype.start = function(e) {
    this.channel.listen();
    $(this).trigger('starting');
};


Notifications.prototype.stop = function(e) {
    this.channel.deafen();
    $(this).trigger('stopping');
};


Notifications.prototype.stopped = function(e) {
    $(this).trigger('stopped');
};


Notifications.prototype.trouble = function(e, xhr) {
    $(this).trigger('trouble');
};


Notifications.prototype.on_message = function(e, data) {
    $(this).trigger('notice.' + data.handler, [data.payload]);
};





var Thread = function() {
    this.channel = new Notifications(window.location + '/live');
    
    $(this.channel).on({
            "notice.locked": $.proxy(this, 'locked'),
            "notice.unlocked": $.proxy(this, 'unlocked'),
            "notice.comment": $.proxy(this, 'commented'),
            
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


Thread.prototype.setState = function(level, state) {
    console.log("Thread.setState", level, state);
    $('.connection-state').removeClass('active disabled').addClass(level);
    $('.connection-state i').addClass('hidden').filter('.' + state).removeClass('hidden');
};


Thread.prototype.locked = function(e, data) {
    console.log("Thread.locked");
};


Thread.prototype.unlocked = function(e, data) {
    console.log("Thread.unlocked");
};


Thread.prototype.commented = function(e, data) {
    console.log("Thread.commented", data.character.name);

    if ( ! data.hasOwnProperty('index') ) return;
    if ( $('#comment-' + data.index).length ) return;
                            
    var template = $('.comment:last').clone();
    
    $('.media-object img', template).attr('src', 'http://image.eveonline.com/Character/' + data.character.nid + '_64.jpg');
    $('.media-object time', template).attr('datetime', data.when.iso).text(data.when.pretty);
    $('.media-body > a', template).attr('href', '/profile/' + data.character.id);
    $('.media-body > a strong', template).text(data.character.name);
    $('.panel-heading', template).remove();
    $('.panel-body', template).html(data.message);
    $('<div class="liner"></div>').insertAfter('.comment:last .media');
    
    template.insertAfter('.comment:last');
};


Thread.prototype.starting = function(e) {
    console.log("Thread.starting");
    this.setState('active', 'connected');
};


Thread.prototype.stopping = function(e) {
    console.log("Thread.stopping");
    this.setState('', 'live');
};


Thread.prototype.stopped = function(e) {
    console.log("Thread.stopped");
    this.setState('', 'disconnected');
};


Thread.prototype.trouble = function(e, xhr) {
    console.log("Thread.trouble");
    this.setState('', 'live')
};
