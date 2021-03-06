'''
Created on Apr 5, 2010

@author: JMS
'''
# This is a fairly large file, so I've cut out a lot of the extra stuff
# that isn't neccessary for this example. Image loading/parsing, gps, etc.

import sys
import gtk
import gobject
try:
    import hildon
    has_hildon = True
except ImportError:
    print "No hildon module"
    has_hildon = False
import threading

import pygst
pygst.require("0.10")
import gst
import time

try:
    import location
    has_location = True
except ImportError:
    print "No location module"
    has_location = False

# My custom data manager module
from BeltConnection import *

# This is ESSENTIAL if you are using multi-threading in a GTK app.  There are
# cleaner ways to do the same using gobject, but I'm using the brute force for
# the sake of sanity
gtk.gdk.threads_init()

# The overall UI form class
class HapticGuideUI:
 # A thread lock, in case needed
 lock = threading.Lock()
 # A frequency of the loop call (in milliseconds)
 TIMEOUT = 500

 def on_window_destroy(self, widget, data=None):
   self.belt.disconnect()
   gtk.main_quit()

 def on_window_delete(self, widget, data=None):
   self.belt.disconnect()
   gtk.main_quit()
   return False

 def on_connect_click(self, widget, data=None):
   self.labelDebugData.set_text("BT Connecting...")
   if self.belt.isConnected == False:
     #self.belt.connect()
     gobject.idle_add(self.belt.connect)
     
     
 def on_GpsConnect_click(self, widget, data=None): 
   self.labelDebugData.set_text("GPS Connecting...") 
   gobject.idle_add(self.start_location, self.control)
   self.labelDebugData.set_text("GPS Connected") 
   
 def on_report_click(self, dummy1, dummy2=None):
    self.labelDebugData.set_text("Clicked")
    self.save_file = True
    return True



 def loop(self):
   # Get latest heading update from belt manager and display update if different from prev
   self.sensor1 = self.belt.sensors[0]
   self.sensor2 = self.belt.sensors[1]
   
   self.sensor1Data.set_text('%d' %(self.sensor1))  
   self.sensor2Data.set_text('%d' %(self.sensor2))
   self.labelCounterData.set_text('%d' %(self.counter))
   
   self.counter+=1
   return True

 def __init__(self):     
   self.save_file = False
   self.screen_sink = None
   self.screen_set_xid = False
   
   try:
       self.app = hildon.Program.get_instance()    
   except:
       self.app = hildon.Program()

   try:
       gtk.set_application_name("C3 Prototype v0.3")
   except:
       pass

   # This is the brilliant GTK+ Glade builder that lets me keep the entire UI
   # code in a .glade (xml) file to be loaded dynamically.
   builder = gtk.Builder()
   builder.add_from_file("sensor.glade") 

   # Get variables to each of the ui widgets we will need to work with
   self.window = builder.get_object("windowMain")
   self.sensor1Data = builder.get_object("labelSensor1Data")
   self.sensor2Data = builder.get_object("labelSensor2Data")
   self.labelCounterData = builder.get_object("labelCounterData")
   self.labelDebugData = builder.get_object("labelDebugData")
   self.labelLatData = builder.get_object("labelLatData")
   self.labelLonData = builder.get_object("labelLonData")
   self.labelDatetime = builder.get_object("labelDatetime")
   self.screen = builder.get_object("screen")
   self.buttonReport = builder.get_object("buttonReport")
   
   self.screen.set_size_request(640, 350)
   self.screen.add_events(gtk.gdk.BUTTON_PRESS_MASK)
   self.screen.connect("expose-event", self.expose_cb, self.screen_sink)
   #self.screen.connect("button_press_event", self.on_report_click)


   # Create the belt object to handle data communication
   self.belt = BeltConnection()

   # Initialize tracking variables
   self.sensor1 = 0
   self.sensor2 = 0
   
   self.counter = 0

   # Connect signals exposed in the glade file to local functions
   signals = { "on_windowMain_destroy_event" : self.on_window_destroy,
               "on_windowMain_delete_event" : self.on_window_delete, 
               "on_buttonBtConnect_clicked" : self.on_connect_click,
               "on_buttonGpsConnect_clicked" : self.on_GpsConnect_click,
               "on_buttonReport_clicked": self.on_report_click
               }
   builder.connect_signals(signals)
   
   if has_location:
       self.control = location.GPSDControl.get_default()
       
       self.device = location.GPSDevice()
       self.control.set_properties(preferred_method=location.METHOD_USER_SELECTED,
                              preferred_interval=location.INTERVAL_DEFAULT)
        
       self.control.connect("error-verbose", self.on_error, self)
       self.device.connect("changed", self.on_changed, self.control)
       self.control.connect("gpsd-stopped", self.on_stop, self)
       
   self.pipeline = gst.Pipeline("c3_camera_pipeline")
   self.labelDebugData.set_text("try")
   self.create_pipeline()

 def expose_cb(self, dummy1, dummy2, dummy3):
    #self.labelDebugData.set_text("Expose event")
    print dummy1
    print dummy1.has_screen()
    print dir(dummy1.get_screen().get_display())
    #self.buffer_cb(self.pad, dummy1.get_screen())
    self.screen_sink.set_xwindow_id(dummy1.window.xid)
    self.screen_set_xid = True
    
 def buffer_cb(self, pad, buffer):
    self.labelDebugData.set_text("buffer_cb")
    if self.save_file:
        self.labelDebugData.set_text("buffer callback")
        self.pipeline.add(self.image_sink)
        self.image_queue.link(self.image_sink)
#        width = 640
#        height = 480
#
#        size = 3 * width * height 
#
#        if buffer.size < size:
#            data = buffer.data + chr(0) * (size-buffer.size)
#        else:
#            data = buffer.data
#
#        self.labelDebugData.set_text("saving buffer")
#        pb = gtk.gdk.pixbuf_new_from_data(data, gtk.gdk.COLORSPACE_RGB, False, 8, width, height, width * 3)
#        pb.save("/home/user/MyDocs/test.jpg", "jpeg", {"quality":"100"})

#        pb2 = pb.scale_simple(120,90,gtk.gdk.INTERP_NEAREST)
#
#        self.labelDebugData.set_text("saving buffer again")
#        pb2.save("/home/user/text_thumbnail.jpg", "jpeg", {"quality":"60"})

        #thumb.clear()
        #thumb.set_from_file("test.jpg")
        #print thumb

        self.save_file = False

    return True

 def on_message(self,bus,message):
    t = message.type
    if t == gst.MESSAGE_EOS:
        self.image_queue.unlink(self.image_sink)
        self.pipeline.remove(self.image_sink)
        self.labelDebugData.set_text("image captured, pipe cut")
    elif t == gst.MESSAGE_ERROR:
        err, debug = message.parse_error()
        print "Error: %s" % err, debug
        self.image_queue.unlink(self.image_sink)
        self.pipeline.remove(self.image_sink)

 def create_pipeline(self):
    self.labelDebugData.set_text("start pipeline")
    src = gst.element_factory_make("v4l2camsrc", "src") 
    src.set_property ("device", "/dev/video0")
    #check dev for video call if this doesn't work
    #src.set_property ("always-copy", True)
    #src.set_property ("width", 640)
    #src.set_property ("height", 480)
    #src.set_property ("framerate", 30)
    #src = gst.element_factory_make("v4l2camsrc", "src")
    self.pipeline.add(src)
    self.bus = self.pipeline.get_bus()
    self.bus.add_signal_watch()
    self.bus.connect("message", self.on_message)
        
    screen_csp = gst.element_factory_make("ffmpegcolorspace", "screen_csp")
    self.pipeline.add(screen_csp)
    
    screen_caps = gst.element_factory_make("capsfilter", "screen_caps")
    # Alternate caps to run outside Internet Tablet (e.g. in a PC with webcam)
    screen_caps.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=640,height=480"))
    #screen_caps.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=640,height=480,bpp=24,depth=24,framerate=30/1"))
    
    self.pipeline.add(screen_caps)
    
    
    image_csp = gst.element_factory_make("ffmpegcolorspace", "image_csp")
    self.pipeline.add(image_csp)
    
    self.image_caps = gst.element_factory_make("capsfilter", "image_caps")
    # Alternate caps to run outside Internet Tablet (e.g. in a PC with webcam)
    self.image_caps.set_property('caps', gst.caps_from_string("video/x-raw-yuv,width=640,height=480"))
    self.pipeline.add(self.image_caps)
    
    
    self.tee = gst.element_factory_make("tee", "tee")
    self.pipeline.add(self.tee)
    
    screen_queue = gst.element_factory_make("queue", "screen_queue")
    self.pipeline.add(screen_queue)
    
    self.screen_sink = gst.element_factory_make("xvimagesink", "screen_sink")
    self.pipeline.add(self.screen_sink)
    
    self.image_encode = gst.element_factory_make("jpegenc", "image_encode")
    self.pipeline.add(self.image_encode)
    
    self.image_queue = gst.element_factory_make("queue", "image_queue")
    self.pipeline.add(self.image_queue)
    
    self.image_sink = gst.element_factory_make("filesink", "image_sink")
    self.image_sink.set_property("location","/home/user/MyDocs/test.jpg")
    #self.pipeline.add(image_sink)
    
    self.pad = self.image_sink.get_pad('sink')
    self.pad.add_buffer_probe(self.buffer_cb)
    
    gst.element_link_many(src, self.tee, screen_caps, screen_csp, screen_queue, self.screen_sink)
    #gst.element_link_many(src, screen_caps, tee, screen_queue, sink)
    gst.element_link_many(self.tee, self.image_caps, image_csp, self.image_queue)
    
    self.window.show_all()
    
    self.pipeline.set_state(gst.STATE_PLAYING)
    
    self.labelDebugData.set_text("end pipeline")
   


 def on_error(self, control, error, data):
    print "location error: %d... quitting" % error
    self.labelDebugData.set_text("location error: %d... quitting" % error)
    self.belt.disconnect()
    gtk.main_quit()

 def on_changed(self, device, data):
    if not device:
        return
    if device.fix:
        if device.fix[1] & location.GPS_DEVICE_LATLONG_SET:
            #print "lat = %f, long = %f" % device.fix[4:6]
            #print device.fix
            self.labelLatData.set_text("%f" % device.fix[4])
            self.labelLonData.set_text("%f" % device.fix[5])
            self.labelDatetime.set_text("%s" % device.fix[2])

 def on_stop(self,control, data):
    print "quitting"
    self.labelDebugData.set_text("quitting..")
    self.belt.disconnect()
    gtk.main_quit()

 def start_location(self, data):
    data.start()
    return False

  

 def show(self):
   self.window.show_all()
   # Add a recurring timeout call so we can continuously update headingsq
   gobject.timeout_add(self.TIMEOUT, self.loop)

if __name__ == "__main__":
 # Show the UI window
 ui = HapticGuideUI()
 ui.show()

 # The threads_enter() and threads_leave() calls are ESSENTIAL for apps with
 # multi-threaded intereaction
 gtk.gdk.threads_enter()
 gtk.main()
 gtk.gdk.threads_leave()