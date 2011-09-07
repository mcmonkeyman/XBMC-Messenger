import xbmc
import xbmcaddon
import xbmcgui
import dbus
import dbus.glib
import gobject
import telepathy
import sys
import os
import csv

from telepathy.interfaces import CLIENT, \
                                 CLIENT_OBSERVER, \
                                 CLIENT_HANDLER, \
                                 CLIENT_APPROVER,\
                                 CHANNEL, \
                                 CHANNEL_TYPE_DBUS_TUBE,\
                                 CONN_INTERFACE,\
                                 ACCOUNT_MANAGER,\
                                 ACCOUNT,\
                                 CHANNEL_DISPATCH_OPERATION
from telepathy.constants import HANDLE_TYPE_ROOM, \
                                SOCKET_ACCESS_CONTROL_LOCALHOST, \
                                CONNECTION_PRESENCE_TYPE_AVAILABLE , \
                                CONNECTION_HANDLE_TYPE_CONTACT, \
                                CONNECTION_HANDLE_TYPE_CONTACT,\
                                CONNECTION_STATUS_CONNECTED,\
                                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL,\
                                CONNECTION_HANDLE_TYPE_CONTACT,\
                                CONNECTION_HANDLE_TYPE_LIST,\
                                CONNECTION_STATUS_CONNECTED,\
                                CONNECTION_STATUS_DISCONNECTED 
#from libs.oldaccount import connection_from_file                                 
from lib.accountmgr import AccountManager
from lib.account import Account


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

#for emulator mode
try: Emulating = xbmcgui.Emulating 
except: Emulating = False
#get actioncodes from keymap.xml 
ACTION_PREVIOUS_MENU = 10
#Set up global list & variables


width =1280
height =1024
AccountList = xbmcgui.ControlList(600, 250, 800, 1000)
ContactList = xbmcgui.ControlList(600, 250, 800, 1000) 
MessagesList = xbmcgui.ControlList(600, 250, 800, 1000) 
Addon = xbmcaddon.Addon( id="script.messenger.testing" )


#Directories
ROOTDIR = Addon.getAddonInfo("path")
ACCOUNTDIR =os.path.join(ROOTDIR, "accounts/")
MESSAGESDIR =os.path.join(ROOTDIR, "messages/")

#Dicsplay settings
TEXT_COLOR="0xF00000FF"
FONT_SIZE="font13"
BUTTON_DIMENSIONS={'width':150,'height':50}

connectionready =False

class MainWindow(xbmcgui.Window):
    def __init__(self):
            

        #Add Dbus service
        self.bus= dbus.SessionBus()
        self.messengerservice= self.bus.get_object('ie.eoin.messenger', '/ie/messenger')
        self.message=self.messengerservice.get_dbus_method('sendmessage','ie.eoin.messenger')
        self.presenceOnline=self.messengerservice.get_dbus_method('putPresenceOnline','ie.eoin.messenger')
        #for emulator mode
        if Emulating: 
            xbmcgui.Window.__init__(self)
        #Add background image
        self.addControl(xbmcgui.ControlImage(0,0,800,600, ROOTDIR+"background.gif"))

    
        #Add Title
        self.strActionInfo = xbmcgui.ControlLabel(width/2, 40, 400, 200, "", FONT_SIZE, TEXT_COLOR) 
        self.addControl(self.strActionInfo) 
        self.strActionInfo.setLabel("Messenger:")


        #Add Buttons
        self.AccountsButton = xbmcgui.ControlButton(width/4, height/4, BUTTON_DIMENSIONS['width'], BUTTON_DIMENSIONS['height'], "Account") 
        self.addControl(self.AccountsButton) 
        

      
        self.CallButton = xbmcgui.ControlButton(width/4, 3*(height/4), BUTTON_DIMENSIONS['width'], BUTTON_DIMENSIONS['height'],  "Call") 
        self.addControl(self.CallButton) 

        self.ChatButton = xbmcgui.ControlButton(3*(width/4), 3*(height/4), BUTTON_DIMENSIONS['width'], BUTTON_DIMENSIONS['height'], "Chat") 
        self.addControl(self.ChatButton) 
        

        self.PresenceButton = xbmcgui.ControlButton(3*(width/4), (height/4), BUTTON_DIMENSIONS['width'], BUTTON_DIMENSIONS['height'], "Presence") 
        self.addControl(self.PresenceButton) 
        self.setFocus(self.PresenceButton)


        #Control for buttons
        self.CallButton.controlRight(self.ChatButton)
        self.CallButton.controlUp(self.AccountsButton)

        self.AccountsButton.controlDown(self.CallButton)
        self.AccountsButton.controlRight(self.PresenceButton)

        self.PresenceButton.controlLeft(self.AccountsButton)
        self.PresenceButton.controlDown(self.ChatButton)

        self.ChatButton.controlUp(self.PresenceButton)
        self.ChatButton.controlLeft(self.CallButton)

        #Initialize and Name ContactList
        global ContactList
        self.addControl(ContactList)
        #ContactList.addItem('Contacts:')
        #self.setFocus(ContactList)


    #All the actions    
    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.message('Closing script')
            self.close()

        		
    def onControl(self, control):

        
        if control == ContactList:
            item = ContactList.getSelectedItem()
            #keyboard
            keyboard = xbmc.Keyboard("mes:") 
            keyboard.doModal()
            if(keyboard.isConfirmed()):
                msg = keyboard.getText()
                #MessagesList.addItem(msg)
                self.SendMessage('eoin4real@gmail.com',msg)
        if control == self.CallButton:
            self.callContactDialog()	

        if control == self.PresenceButton:
            keyboard = xbmc.Keyboard("") 
            keyboard.doModal()
            if(keyboard.isConfirmed()):
                pres = keyboard.getText()
                
                #Send the message      
                print self.presenceOnline(pres)
        if control == self.AccountsButton:
            pass	
        if control == self.ChatButton:
            dchat = ChatWindow()
            dchat .doModal()
            del dchat


			
    def message(self, message):
        dialog = xbmcgui.Dialog()
        dialog.ok(" My message title", message)

    def callContactDialog(self):
        dialog = xbmcgui.Dialog()
        if dialog.yesno("message", "do you want to call a contact?"):

            keyboard = xbmc.Keyboard("") 
            keyboard.doModal()
            if(keyboard.isConfirmed()):
                contact = keyboard.getText()
                command =os.path.join(ROOTDIR, "makecall.py")
                argument = os.path.join(ACCOUNTDIR, "DefaultAccount")
                print 'running:'+command+' '+argument+' "'+contact+'"'
                #xbmc.executescript(command+' '+argument+' "eoin4real@gmail.com"')
                xbmc.executebuiltin("XBMC.RunScript("+command+","+argument+",eoin4real@gmail.com)")

class ChatWindow(xbmcgui.Window):
    def __init__(self):
        self.strActionInfo = xbmcgui.ControlLabel(width/2, 40, 400, 200, '', FONT_SIZE, TEXT_COLOR)
        self.addControl(self.strActionInfo)
        self.strActionInfo.setLabel('Chat Window')
        self.list = xbmcgui.ControlList(200, 150, 300, 400)
        self.addControl(self.list)
        addMessagesToList('2',self.list)
        self.setFocus(self.list)


        self.bus= dbus.SessionBus()
        self.messengerservice= self.bus.get_object('ie.eoin.messenger', '/ie/messenger')
        self.messageclient=self.messengerservice.get_dbus_method('sendmessage','ie.eoin.messenger')
 
    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()
 
    def onControl(self, control):
        if control == self.list:
            item = self.list.getSelectedItem()
            #self.message('You selected : ' + item.getLabel())  
            keyboard = xbmc.Keyboard("") 
            keyboard.doModal()
            if(keyboard.isConfirmed()):
                msg = keyboard.getText()
                
                #Send the message      
                print self.messageclient(msg)

    def message(self, message):
        dialog = xbmcgui.Dialog()
        dialog.ok(" My message title", message)

#Utitlity Functions
  
def addMessagesToList(file_name,listToAdd):
    print MESSAGESDIR + file_name +'.txt'
    log_file =open( MESSAGESDIR + file_name +'.txt','r')
    for line in log_file:
        listToAdd.addItem(line[:-1])
  
if __name__ =="__main__":	
    mydisplay = MainWindow() 


    mydisplay.doModal()
   
    
    
    xbmc.executebuiltin("xbmc.Notification(Script Closed ,The Messenger Script has been closed ,30)")
    del mydisplay
