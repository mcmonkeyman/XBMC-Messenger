import dbus
import dbus.glib
import gobject
import sys
import gst

import tpfarsight
import farsight

from lib.oldaccount import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE, CONNECTION_HANDLE_TYPE_CONTACT,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED,
    MEDIA_STREAM_TYPE_AUDIO, MEDIA_STREAM_TYPE_VIDEO)
from telepathy.interfaces import (
    CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_STREAMED_MEDIA,
    CONN_INTERFACE, CONN_INTERFACE_CAPABILITIES, CONNECTION)

import logging
logging.basicConfig()
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

class Call:
    def __init__(self, connection,contact):
         
        self.conn=connection_from_file(connection,ready_handler=self.ready_cb)
    
        #Get arguments and set channels 
        self.contact = contact
        self.channel = None
        self.fschannel = None
        self.calling = False

        #Set up pipeline
        self.pipeline = gst.Pipeline()
        self.pipeline.get_bus().add_watch(self.async_handler)

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',self.status_changed_cb)
        self.conn[CONN_INTERFACE].connect_to_signal('NewChannel',self.new_channel_cb)

        
       
    def  ready_cb(self,connection):
        self.handle = handle = self.conn[CONN_INTERFACE].RequestHandles(CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]
        self.start_call()

    def async_handler (self, bus, message):
        if self.tfchannel != None:
            self.tfchannel.bus_message(message)
        return True

    def run_main_loop(self):
        self.loop = gobject.MainLoop()
        self.loop.run()

    def run(self):
        
        self.conn[CONN_INTERFACE].Connect()
        print "connecting"
      
        try:
            self.run_main_loop()
        except KeyboardInterrupt:
            print "killed"

            if self.channel:
                print "closing channel"
                self.channel[CHANNEL_INTERFACE].Close()

        try:
            print "disconnecting"
            self.conn[CONN_INTERFACE].Disconnect()
        except dbus.DBusException:
            pass

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_DISCONNECTED:
            print 'connection closed'
            self.quit()

    

    def request_channel_error_cb(self, exception):
        print 'error:', exception
        self.quit()

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
            suppress_handler):
        if channel_type == CHANNEL_TYPE_STREAMED_MEDIA:
            self.chan_handle_type = handle_type
            self.chan_handle = handle
            print "new streamed media channel"
            Channel(self.conn.service_name, object_path,ready_handler=self.channel_ready_cb)
        else:
            return


    def src_pad_added (self, stream, pad, codec):
        type = stream.get_property ("media-type")
        if type == farsight.MEDIA_TYPE_AUDIO:
            sink = gst.parse_bin_from_description("audioconvert ! audioresample ! audioconvert ! autoaudiosink", True)
        self.pipeline.add(sink)
        pad.link(sink.get_pad("sink"))
        sink.set_state(gst.STATE_PLAYING)

    def stream_created(self, channel, stream):
        stream.connect ("src-pad-added", self.src_pad_added)
        srcpad = stream.get_property ("sink-pad")

        type = stream.get_property ("media-type")

        if type == farsight.MEDIA_TYPE_AUDIO:
            print 'audio'
            #gconfaudiosrc
            #audiotestsrc
            #alsasrc
            src = gst.element_factory_make ("gconfaudiosrc")
            #src.set_property("is-live", True)

        self.pipeline.add(src)
        src.get_pad("src").link(srcpad)
        src.set_state(gst.STATE_PLAYING)

    def session_created (self, channel, conference, participant):
        self.pipeline.add(conference)
        self.pipeline.set_state(gst.STATE_PLAYING)

   

    def channel_ready_cb(self, channel):
        print "channel ready"
        channel[CHANNEL_INTERFACE].connect_to_signal('Closed', self.closed_cb)
        channel[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged',self.members_changed_cb)
        channel[CHANNEL_TYPE_STREAMED_MEDIA].connect_to_signal('StreamError', self.stream_error_cb)

        self.channel = channel

        tfchannel = tpfarsight.Channel(self.conn.service_name,
            self.conn.object_path, channel.object_path)

        self.tfchannel = tfchannel
        tfchannel.connect ("session-created", self.session_created)
        tfchannel.connect ("stream-created", self.stream_created)

        print "Channel ready"

        channel[CHANNEL_INTERFACE_GROUP].AddMembers([self.handle], "")

        print "requesting audio/video streams"

        try:
            channel[CHANNEL_TYPE_STREAMED_MEDIA].RequestStreams(self.handle,[MEDIA_STREAM_TYPE_AUDIO]);
                
        except dbus.DBusException, e:
            print "failed:", e
            print "giving up"
            self.quit()

    def stream_error_cb(self, *foo):
        print 'error: %r' % (foo,)
        self.channel.close()

    def closed_cb(self):
        print "channel closed"
        self.quit()

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        print 'MembersChanged', (
            added, removed, local_pending, remote_pending, actor, reason)


    def start_call(self):
        self.calling = True
        self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_STREAMED_MEDIA, CONNECTION_HANDLE_TYPE_NONE,
            0, True, reply_handler=lambda *stuff: None,
            error_handler=self.request_channel_error_cb)

   



if __name__ == '__main__':
    gobject.threads_init()
    
    args = sys.argv[1:]



    if len(args) == 2:
        call = Call(args[0], args[1])
    else:
        print 'error wrong inputs'

    call.run()
