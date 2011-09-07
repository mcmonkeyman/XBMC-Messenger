import xbmc
import xbmcaddon
import xbmcgui
import dbus
import dbus.glib
import dbus.service
import gobject
import telepathy
import sys
import os
import csv


#from libs.oldaccount import connection_from_file                                 
from lib.accountmgr import AccountManager
from lib.account import Account


from telepathy.interfaces import CLIENT, \
                                 CLIENT_OBSERVER, \
                                 CLIENT_HANDLER, \
                                 CLIENT_APPROVER,\
                                 CHANNEL, \
                                 CHANNEL_TYPE_DBUS_TUBE,\
                                 CONN_INTERFACE,\
                                 ACCOUNT_MANAGER,\
                                 ACCOUNT,\
                                 CHANNEL_DISPATCH_OPERATION, \
                                 CHANNEL_TYPE_TEXT,CHANNEL_TYPE_STREAMED_MEDIA, CHANNEL, \
                                 CHANNEL_INTERFACE_MESSAGES                                   
from telepathy.constants import HANDLE_TYPE_ROOM, \
                                SOCKET_ACCESS_CONTROL_LOCALHOST, \
                                CONNECTION_PRESENCE_TYPE_AVAILABLE, CONNECTION_PRESENCE_TYPE_OFFLINE, \
                                CHANNEL_TEXT_MESSAGE_TYPE_DELIVERY_REPORT, \
                                HANDLE_TYPE_CONTACT, \
                                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL

#For XBMC
Addon = xbmcaddon.Addon( id="script.messenger.testing" )
ROOTDIR = Addon.getAddonInfo("path")
ACCOUNTDIR =os.path.join(ROOTDIR, "accounts/")
MESSAGESDIR =os.path.join(ROOTDIR, "messages/")


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'
connections={}
accounts={}


######CLIENT######

class MessengerClient(
                    #telepathy.server.Observer,
                    telepathy.server.Handler,
                    telepathy.server.Approver,
                    telepathy.server.DBusProperties):

    def __init__(self, *args):

        #Connect to GUI, get D-Bus, create maps and intilize variables.

        self._channels = []
        self.bus = dbus.SessionBus()
                
        #Initialize Telepathy and D-Bus
        client_name= args[0]
        bus_name = '.'.join ([CLIENT, client_name])
        object_path = '/' + bus_name.replace('.', '/')
        bus_name = dbus.service.BusName(bus_name, bus=dbus.SessionBus())
        args=(bus_name,object_path)
        dbus.service.Object.__init__(self,*args)
        telepathy.server.DBusProperties.__init__(self)
      
        #Setup MessengerClient to be Telepathy Handler.
        self._implement_property_get(CLIENT, {
            'Interfaces': lambda: [  CLIENT_HANDLER],
            # CLIENT_OBSERVER,, CLIENT_APPROVER 
          })
        self._implement_property_get(CLIENT_HANDLER, {
            'HandlerChannelFilter': lambda: dbus.Array([
                    dbus.Dictionary({
                        'org.freedesktop.Telepathy.Channel.ChannelType':      CHANNEL_TYPE_TEXT,
                        'org.freedesktop.Telepathy.Channel.TargetHandleType': HANDLE_TYPE_CONTACT
                    }, signature='sv'),
                    dbus.Dictionary({
                        'org.freedesktop.Telepathy.Channel.ChannelType':      CHANNEL_TYPE_STREAMED_MEDIA,
                        'org.freedesktop.Telepathy.Channel.TargetHandleType': HANDLE_TYPE_CONTACT,
                        #'org.freedesktop.Telepathy.Channel.Requested':        True,
                    }, signature='sv')
                ], signature='a{sv}'),
            'BypassApproval': lambda: False,
            'Capabilities': lambda: dbus.Array([], signature='s'),
            'HandledChannels': self.get_handled_channels,
          })

        

    def AddAccount(self):
        
        accountmanager= AccountManager()
        

    def ConnectToAccounts(self):
        "Connect to any active accounts the Account Manager has." 

        
        accountmanager= AccountManager()
    
        #loop through every account in the Account Manager and connect.
        for acct_path in accountmanager[DBUS_PROPERTIES].Get(ACCOUNT_MANAGER, 'ValidAccounts'):
            self.account=acct = Account(acct_path)        
            conn_path = acct[DBUS_PROPERTIES].Get(ACCOUNT, 'Connection')
            service_name = acct[DBUS_PROPERTIES].Get(ACCOUNT, 'Service')
      
            conn_name =conn_path.replace('/', '.')[1:]
            
            Presence= 'Logged In From XBMC'
            if conn_path == '/':
                acct.Set('org.freedesktop.Telepathy.Account', 'RequestedPresence',
                    dbus.Struct((dbus.UInt32(CONNECTION_PRESENCE_TYPE_AVAILABLE),Presence,Presence),signature='uss'),        
                    dbus_interface='org.freedesktop.DBus.Properties',
                    reply_handler=self.account_status_changed_cb,
                    error_handler=self.error_cb)
                
                continue
        
            self.conn=conn = telepathy.client.Connection(conn_name, conn_path)
            conn.call_when_ready(connection_ready_cb)
            conn[CONN_INTERFACE].Connect()

            connections[conn_path]=conn
            accounts[acct_path]=acct
            # note: the next step takes place in Example.ready_cb()
    

    
    
    def account_status_changed_cb(self):
        print 'account status changed'
        self.ConnectToAccounts()
     
        
     
    def DisconnectFromAccounts(self):
        #Disconnect from accounts and connections

        for name,account in accounts.iteritems():
            self.RequestPresenceOffline(account)
        for name,connection in connections.iteritems():
            try:
                print "Attempting to disconnect %s:%s"%(name,connection)    
                connection[CONN_INTERFACE].Disconnect()
                
            except Exception,e:
                print "Error  disonnecting"
                print e
        print "Disconnectied from accounts"

  
    def RequestPresenceOffline(self,acct):
        acct.Set('org.freedesktop.Telepathy.Account', 'RequestedPresence',
                    dbus.Struct((dbus.UInt32(CONNECTION_PRESENCE_TYPE_OFFLINE),'',''),signature='uss'),        
                    dbus_interface='org.freedesktop.DBus.Properties',
                    reply_handler=self.account_status_changed_cb,
                    error_handler=self.error_cb)

    def RequestPresenceOnline(self,pres):
        self.account.Set('org.freedesktop.Telepathy.Account', 'RequestedPresence',
                    dbus.Struct((dbus.UInt32(CONNECTION_PRESENCE_TYPE_AVAILABLE),pres,pres),signature='uss'),        
                    dbus_interface='org.freedesktop.DBus.Properties',
                    reply_handler=self.account_status_changed_cb,
                    error_handler=self.error_cb)

    def HandleChannels(self, account, connection, channels, requests_satisfied,
                       user_action_time, handler_info):

        print "Handling Operation "
        service_name = connection[1:].replace('/', '.')

        for c in channels:           
            #print 'connectin to channel channel("%s", "%s")' % ( service_name, c[0])
            
            if c[1][CHANNEL+'.ChannelType'] == CHANNEL_TYPE_TEXT:
                self.tchannel=TextChannel(self, c[0])         
                
            
           

    def error_cb(self, error):
        print "Error: %s" % error

    def get_handled_channels(self):
        print " Get Handled Channels"
        return dbus.Array([ c.object_path for c in self._channels ],
            signature='o')

    def send_message(self,msg):
        try:
            self.tchannel.send_message(msg)
        except Exception,e:
            print e

    def SetLoop(self,loop):
        self.loop=loop

    def quit(self):
        self.loop.quit()

class TextChannel (telepathy.client.Channel):
    def __init__ (self, parent, channel_path):
        print "New Text channel.."
        self.parent = parent
        conn = parent.conn
        
        super (TextChannel, self).__init__ (conn.service_name, channel_path)
      
      
        channel = self

        channel[DBUS_PROPERTIES].Get(CHANNEL, 'Interfaces',reply_handler = self.interfaces_cb,error_handler = self.parent.error_cb)
        print "...created"
    
    def interfaces_cb (self, interfaces):
        channel = self


        if CHANNEL_INTERFACE_MESSAGES in interfaces:
            channel[CHANNEL_INTERFACE_MESSAGES].connect_to_signal('MessageReceived', self.message_received_cb)
            channel[CHANNEL_INTERFACE_MESSAGES].connect_to_signal('PendingMessagesRemoved', self.pending_messages_removed_cb)

            # find out if we have any pending messages
            channel[DBUS_PROPERTIES].Get(CHANNEL_INTERFACE_MESSAGES,'PendingMessages',reply_handler = self.get_pending_messages,error_handler = self.parent.error_cb)

    def get_pending_messages (self, messages):
        for message in messages:
            self.message_received_cb (message)

    def message_received_cb (self, message):
        channel = self
         
        # Acknowledge messages
        msg_id = message[0]['pending-message-id']
        channel[CHANNEL_TYPE_TEXT].AcknowledgePendingMessages([msg_id],reply_handler = void,error_handler = self.parent.error_cb)

        
        if (xbmc.Player().isPlayingVideo()): 
            xbmc.Player().pause()


        #Record Message
        ##Print to output

        print '-' * 78
        print 'Received Message:'
        for d in message:
            print '{'
            for k, v in d.iteritems():
                print '  %s: %s' % (k, v)
            print '}'
        print '-' * 78

        
        xbmc.executebuiltin("xbmc.Notification(Message Received,"+message[1]['content'] +",30)")
        
        ##Log message to CSV file
        log_file =open( MESSAGESDIR + str(message[0]['message-sender']) +'.txt','a')
        log_file.write(message[1]['content']+'\n')
        log_file.close()
        

        # Echo
        #self.send_message('Echo:'+message[1]['content'])
        


    def send_message(self,msg):

        channel = self

        new_message = [
            {}, # let the CM fill in the headers
            {
                'content': '%s' % msg, 
                'content-type': 'text/plain',
            },
        ]
        channel[CHANNEL_INTERFACE_MESSAGES].SendMessage(new_message, 0,reply_handler = self.send_message_cb,error_handler = self.parent.error_cb)
        
    def pending_messages_removed_cb (self, message_ids):
        print "Acked messages %s" % message_ids

    def send_message_cb (self, token):
        print "Sending message with token %s" % token
def void(*args):
    pass


def connection_ready_cb(connection):
    print 'connected to account'

class MyDBUSService(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName('ie.eoin.messenger', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/ie/messenger')
 
        print 'serviceSetup'

    
    @dbus.service.method('ie.eoin.messenger', in_signature='s', out_signature='s')
    def sendmessage(self,s):
        print "tryingtosend...."
        client.send_message(s)
        print "...sent"
        return "Sent"


    @dbus.service.method('ie.eoin.messenger', in_signature='s', out_signature='s')
    def putPresenceOnline(self,s):
        client.RequestPresenceOnline(s)
        return "Requested"

    @dbus.service.method('ie.eoin.messenger', in_signature='s', out_signature='s')
    def putPresenceOffline(self,s):
        pass
    def addclient(self,client):
        self.client=client
if __name__ == '__main__':

    #Make  the Messenger Client
    client = MessengerClient( 'MessengerClient')

    #Connect to any active accounts the Account Manager Has.
    client.ConnectToAccounts()
    
    #Make Loop
    loop = gobject.MainLoop()
    
    client.SetLoop(loop)
    
    #Create Service for front end to communicate with
    myservice = MyDBUSService()
    myservice.addclient(client)
    
    try:
        gobject.threads_init()
        loop.run()
    except KeyboardInterrupt:
        print "killed"
        #Disconnect the connected accounts on the Account Manager
        client.DisconnectFromAccounts()
    xbmc.executebuiltin("xbmc.Notification(Script Closed ,The Messenger Script has been closed ,30)")
   
    
