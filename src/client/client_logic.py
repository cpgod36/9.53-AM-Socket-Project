from tkinter import *
from tkinter import messagebox as tkMessageBox
from PIL import Image, ImageTk
import io
import sys
import os

# Import Core Logic vừa tách
try:
    from src.client.rtsp_core import RtspClientCore
except ImportError:
    try:
        from rtsp_core import RtspClientCore
    except ImportError:
        import sys, os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from rtsp_core import RtspClientCore

class Client:
    """
    Class này CHỈ CHỨA code giao diện Tkinter.
    Mọi logic mạng đã chuyển sang self.core (RtspClientCore).
    """
    
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        
        self.core = RtspClientCore(serveraddr, serverport, rtpport, filename, self.updateMovie)
        
        success = self.core.connect_server()
        if not success:
            tkMessageBox.showwarning('Connection Failed', f'Connection to {serveraddr} failed.')

    def createWidgets(self):
        """Build GUI."""
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.setupMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)
        
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)
        
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)
        
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] =  self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)
        
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
        self.label.configure(text="Ready to connect...")
    
    def setupMovie(self):
        self.core.send_setup()
    
    def playMovie(self):
        self.core.send_play()
    
    def pauseMovie(self):
        self.core.send_pause()
    
    def exitClient(self):
        self.core.send_teardown()
        self.master.destroy()

    def updateMovie(self, imageBytes):
        try:
            image_stream = io.BytesIO(imageBytes)
            image = Image.open(image_stream)
            photo = ImageTk.PhotoImage(image)
            self.label.configure(image=photo, height=288) 
            self.label.image = photo
        except Exception as e:
            print(f"Error updating image: {e}")

    def handler(self):
        self.core.send_pause()
        if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:
            self.core.send_play()