# -*- coding: utf-8 -*-
import numpy as np
import argparse
import cv2
import cv2.cv as cv
import time
import datetime
import ftplib

import random

from threading import Timer, Thread, Event #Threading für Testmodul

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import smtplib


#==================================================
# PREFS
#==================================================

#Define Betriebszeitem
betriebStart = 9 # Startet ab x:00 Uhr
betriebEnde = 18 # Endet um x:00 Uhr
mittagStart = 12
mittagEnde = 14
betriebAnwenden = True #Flag, um den Betriebsschluss zu ignorieren. True respektier, False ignoriert

#Define Testmode:
test = False #'True' startet Testmodus ohne Kameraabfrage, 'False' nutzt die Kamera
testSekunden = 20 #Alle wieviel Sekunden erhöht sich der Kreiszähler im Testmodus

#Define Stufen
stufeDelta = 5 #Alle wieviel Tassen und Teller soll sich die Warnstufe erhöhen (default = 5)
circlesMessungen = 30 #Aus wievielen Messungen soll der Durchschnitt gebildet werden?
maxVergessen = 5; #wieviele Maximalwerte sollen rausgerechnet werden, um Köpfe zu ignorieren?
mailPause = 30 # Wieviele Minuten soll zwischen zwei Mails liegen?(Def. 30)
 
# Define Mail
strFrom = 'testgmail.com' #Auch: Login fuer Mail-Versand
mailPwd = 'pwd'

#Define ftp
ftpUser = 'usr'
ftpPwd = 'pwd'

#Define Region of interest
x_min = 100 #kleinste x-Koordinate, die bercksichtigt werden soll
x_max = 500 #größte x-Koordinate
y_min = 100 # kleinste y-Koordinate
y_max = 400 # größte y-Koordinate


#==================================================
# Declarations
#==================================================

#Handling für die unterschiedlichen Stufen
stufe = 0
letzteStufe = 0

betriebsMessage = False #Flag, damit wir zum Betriebsschluss eine Message ausgeben

letztesUpdate = time.time() #Initialstart
letzteMail = time.time() # Initial letzter Mailversans

recipients = None

circlesSumme = [0]* circlesMessungen

poebelText = [['Was ist das denn für ein Saustall?','Wenn du alles wegräumst, gibt es morgen schönes Wetter','Was sollen denn die Nachbarn denken?','Das räumt sich nicht von selber weg!', 'Wie sieht das denn hier wieder aus?'], ['Du bist genauso schlampig wie V.A.D.D.I.', 'Ich sag es dir noch EINMAL im Guten.', 'Fang an, die Leute gucken schon!', 'Wenn das alle so machen würden!', 'Mit dieser Schlamperei endest du in der Gosse', 'Hier sieht’s ja aus, als hätte eine Bombe eingeschlagen'], ['Wer nicht hören will muss spülen', 'Gleich klatsch es, aber kein Beifall...', 'Ich bin so enttäuscht von dir', 'Es gibt gleich einen mit dem Kochlöffel.', 'Warum muss ich immer alles dreimal sagen?', 'Solange du deine Füße unter meinen Tisch stellst, herrscht hier MEINE Ordnung.']]
sublineText = ['Wie bei den Hottentotten!', 'Und lass nicht wieder alles fallen.', 'Das hätte es früher nicht gegeben!']
betreffText = ['Komm rum: es warten %s Tassen und Teller in der Kueche...', '**Jetzt aber flott! %s Tassen und Teller in der Kueche.', '***GLEICH SETZT ES WAS! Jetzt stehen %s Tassen und Teller in der Kueche']

cap = cv2.VideoCapture(0) # Set Capture Device, in case of a USB Webcam try 1, or give -1 to get a list of available devices

overcolor = cv2.imread('/home/pi/Pictures/overlay_muddivision.png') # Bild laden (wird automatisch mit 3 kanälen geladen)
over = cv2.cvtColor(overcolor, cv2.COLOR_BGR2GRAY)   # Kanäle reduzieren

#==================================================
# Versions
#==================================================

# Version dish_02: stackoverflow "using houghcircles". Works. Detects not enough circles
# Version dish_03: Playimng with params
# Version dish_04: Saving pic to Picture_Folder
# Version dish_06: Improved Email Script. Works. Opening/Closing server maybe just once?
# Version dish_07: Send HTML-Mails. Works.
# Version dish_08: Adapting to kitchen
# Version dish_09: Adjust pic to llok
# Version dish_10: ftp-upload
# Version dish_11: send complex mail
# Version dish_12: add goggle spreadsheet module
# Version dish_13: based on 11, new structure
# Version dish_14: testModul and time handling added
# Version dish_15: Neue Schleife
# Version dish_16: Fix Darstellung
# Version dish_17: Ändere Testmodul in auto-Thread
# Version dish_18: Aufräumen. Betribesschluss hinzu
# version dish_19: Textvarianten
# version dish_20: Messungen glätten, Stages einführen
# version dish_21: Mail-Abfrage
# version dish_22: Timestamp für Bilder
# version dish_23: Optimierungen Tassenzählungen
# version dish_24: Sendepause zwischen zwei Mails
# version dish_25: Betreff optimiert, p-Handling
# version dish_26: Region of interest
# version dish_27: roi ins Bild einblenden
# version dish_28: roi fixed
# version dish_30: texte update
# version dish_31: Texte Korrektur
# version dish_32: Mittagszeiten ausklammern, Bug Löschung "recipients"
# version dish_33: Logfile Handling
# version dish_34: Threading OK, dataFile einlesen OK
# version dish_35: Threading beenden ...
# Version dish_36: basiert auf 32. Extreme löschen

def formatierteZeit():
        return time.strftime('%y%m%d%H%M%S', time.localtime(time.time()))

def mailAbfrage():
        mailEingabe = ""
        empfaenger = None
        ok = 'n'
        counter = 1

        while(ok.lower() != 'j'):
                print('')
                print('------------------------------------------------------------------------')
                print(' Eingabe der Empfänger')
                print('------------------------------------------------------------------------')
                print('')
                print('Bitte Empfänger als vorname.nachname ohne "@ggh-mullenlowe.de" eingeben')
                print('"*" beendet Eingabe. Ohne Name werden nur Testmails an Oliver versendet.')
                print('')
                
                while(mailEingabe != '*'):
                        mailEingabe = raw_input('%s. Empfänger > ' % counter)
                        
                        if empfaenger is None:
                                empfaenger = [mailEingabe + '@ggh-mullenlowe.de'] #Erste Eingabe 
                        else:
                                empfaenger.append(mailEingabe + '@ggh-mullenlowe.de') #Weitere Eingaben
                        counter += 1
                else:
                        print('')
                        print('Bitte Eingaben kontrollieren:')
                        
                        del empfaenger[-1] #letzten Einträge verlieren
                        
                        if len(empfaenger) == 0: #leere Liste, senden Testmail an mich
                                empfaenger = ['oliver.heidorn@ggh-mullenlowe.de']
                                
                        for i in empfaenger:
                                print("> " + i)
                        print('')
                        ok = raw_input('Eingabe OK? (j/n) > ')
                        if ok.lower() == 'j':
                                print('')
                                break
                        
                        mailEingabe = "" #nächste Runde, zurücksetzen
                        del empfaenger[:]
                        counter = 1
                        
        return(empfaenger)
                        
                  
        

def camModule(cap):
        # Capture frame-by-frame
        circles = []
        ret, frame = cap.read()

        # load the image, clone it for output, and then convert it to grayscale
                
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        graycopy = gray.copy()
        
        # apply GuassianBlur to reduce noise. medianBlur is also added for smoothening, reducing noise.
        gray = cv2.GaussianBlur(gray,(5,5),0);
        gray = cv2.medianBlur(gray,5)
        
        # Adaptive Guassian Threshold is to detect sharp edges in the Image. For more information Google it.
        gray = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
            cv2.THRESH_BINARY,11,3.5)
        
        kernel = np.ones((2.6,2.7),np.uint8)
        gray = cv2.erode(gray,kernel,iterations = 1)
        # gray = erosion
        
        gray = cv2.dilate(gray,kernel,iterations = 1)
        gray_roi = gray[y_min:y_max, x_min:x_max] #roi-Werte definieren, um den Viewport einzuschränken
        # gray = dilation
        
        # detect circles in the image
        circles_roi = cv2.HoughCircles(gray_roi, cv.CV_HOUGH_GRADIENT, 1.9, 50, param1=5, param2=50, minRadius=8, maxRadius=55)
        #1.2, 50, param1=50, param2=40, minRadius=10, maxRadius=70 = OK, grosse Kreise in der Luft, 50 % der kleinen bei KL
        # 
        #Tasse = 30 px 
        # print circles
        
        cv2.rectangle(over, (x_min, y_min), (x_max, y_max), (255,255,255) ,2) # Linien aufs Overlay malen
        output = cv2.addWeighted(graycopy, 1, over, 0.1, 0.5) # halbtransparent zusammenführern
        
        
        # ensure at least some circles were found
        if circles_roi is not None:
                # convert the (x, y) coordinates and radius of the circles to integers
                circles_roi = np.round(circles_roi[0, :]).astype("int")
                
                # loop over the (x, y) coordinates and radius of the circles
                for i, (x, y, r) in enumerate(circles_roi):
                        # draw the circle in the output image, then draw a rectangle in the image
                        # corresponding to the center of the circle
                        #cv2.circle(output, (x + x_min, y + y_min), r, (0, 0, 0), 2) #addiere roi-werte, sonst verschobene
                        cv2.circle(output, (x + x_min -2, y + y_min -2), r, (255, 255, 255), 2)

                        circles.append([x + x_min, y + y_min, r]) # roi-werte addieren. Sonst stimmen Koordinaten nicht (optional)

                        #print "Number of circles detected:"
                        #print len(circles)

        # Display the resulting frame
        
        cv2.imshow('M.U.D.D.I.-Vision',output)
        cv2.imwrite('/home/pi/Pictures/dishtracker.png', output)
        

        if cv2.waitKey(1) & 0xFF == ord('q'):
                pass
        
        #time.sleep(10)      
        return(circles)

def mailConstruct(poebel, fileName, subline):
        
        htmlMessage = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
        <!-- If you delete this tag, the sky will fall on your head -->
        <meta name="viewport" content="width=device-width" />

        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <title>M.U.D.D.I.</title>
                
        <link rel="stylesheet" type="text/css" href="http://oliverheidorn.de/muddi/stylesheets/email.css" />

        </head>
         
        <body bgcolor="#FFFFFF">

        <!-- HEADER -->
        <table class="head-wrap" bgcolor="#FFFFFF">
                <tr>
                        <td></td>
                        <td class="header container">
                                
                                        <div class="content">
                                                <table bgcolor="#FFFFFF">
                                                <tr>
                                                        <td><img src="http://oliverheidorn.de/muddi/header_ornament_560.png" /></td>
                                                </tr>
                                        </table>
                                        </div>
                                        
                        </td>
                        <td></td>
                </tr>
        </table><!-- /HEADER -->


        <!-- BODY -->
        <table class="body-wrap">
                <tr>
                        <td></td>
                        <td class="container" bgcolor="#FFFFFF">

                                <div class="content">
                                <table>
                                        <tr>
                                                <td>
                                                        
                                                        <h3>„%s“</h3>
                                                        
                                                        <!-- A Real Hero (and a real human being) -->
                                                        <p><img src="http://oliverheidorn.de/muddi/%s" /></p><!-- /hero -->
                                                        
                                                        <!-- Callout Panel -->
                                                        <p class="callout">
                                                                „%s“ 
                                                        </p><!-- /Callout Panel -->
                                                        
                
                                                        
                                                        <h4>Warum bekommst du diese Mail? </h4>
                                                        <p>Du hast Küchendienst und „M.U.D.D.I.“ hat in der letzten halben Stunde ziemlich viele Teller und Tassen auf dem Tresen gezählt. </p> 
                                                        <p>„M.U.D.D.I.“ ist die <i>Maternal Unit for Dish Detection & Instruction</i> und passt mit mütterlicher Sorgfalt auf, dass nicht soviel auf dem GGH-Küchentresen rumsteht. </p>
                                                        <p> Das System ist ein Versuchsprojekt – wenn etwas gründlich schief geht, dann klick einfach auf den Button und schreib, was V.A.D.D.I. verbessern kann.</p>
                                                        <br/>
                                                        <br/>
                                                        <a class="btn"; href="mailto:probierstube@gmail.com">Problem melden</a>
                                                                                                        
                                                        <br/>							
                                                                                                        
                                                        <!-- social & contact -->
                                                    <!-- deleted -->
                                                
                                                </td>
                                        </tr>
                                </table>
                                </div>
                                                                                
                        </td>
                        <td></td>
                </tr>
        </table><!-- /BODY -->

        <!-- FOOTER -->

        <table class="head-wrap" bgcolor="#FFFFFF">
                <tr>
                        <td></td>
                        <td class="header container">
                                
                                        <div class="content">
                                                <table bgcolor="#FFFFFF">
                                                <tr>
                                                        <td><img src="http://oliverheidorn.de/muddi/footer_ornament_560.png" /></td>
                                                </tr>
                                        </table>
                                        </div>
                                        
                        </td>
                        <td></td>
                </tr>
        </table><!-- /HEADER -->
        <!-- /FOOTER -->

        </body>
        </html>"""

        htmlMessageComplete = htmlMessage % (poebel, fileName, subline)

        return(htmlMessageComplete)
        

while(True):
        #while(True): #override Betriebsschluss
        while((datetime.datetime.today().weekday()>= 0 and datetime.datetime.today().weekday()< 5 and ((datetime.datetime.now().hour >= betriebStart and datetime.datetime.now().hour < mittagStart) or (datetime.datetime.now().hour >= mittagEnde and datetime.datetime.now().hour < betriebEnde))) or not betriebAnwenden): #Betriebszeiten Wochentag Uhrzeit

                if recipients is None:
                        recipients = mailAbfrage()

                betriebsMessage = False #Flag zurücksetzen, damit sie beim nächsten Betriebsschluss Mledung ausgibt


                # Je nach Testmodus circles eine Zahl zuweisen
                if test == True: 
                        circles = [0] * (int((time.time() - letztesUpdate) / testSekunden))
                else:
                        circles = camModule(cap)
                        
                # circlesAnzahl einen Wert zuweisen
                if circles is not None:
                        circlesAnzahl = len(circles) 
                else:
                        circlesAnzahl = 0

                print('%s: %s Kreise erkannt' % (formatierteZeit(), circlesAnzahl))


                # Wenn die Summe gefüllt ist, dann ältesten wegpoppen
                if len(circlesSumme) >= circlesMessungen:
                        circlesSumme.pop(0)
                        
                circlesSumme.append(circlesAnzahl) # Summe füllen
                circlesGlatt = sorted(circlesSumme)[:(len(circlesSumme) - maxVergessen)] # Maximalwerte rausrechnen
                #print('%s: %s Kreise in der Variable' % (formatierteZeit(), len(circlesGlatt)))
                circlesDurchschnitt = sum(circlesGlatt)/len(circlesGlatt) #Durchschnitt errechnen

                if int(time.time() - letzteMail) > mailPause * 60: #Stufe wird nur upgedatet, wenn Mailversand öglich ist
                        stufe = int((circlesDurchschnitt / stufeDelta))
                else:
                        print('%s: Nächster Mailversand in %s. Sekunden möglich' % (formatierteZeit(), abs(int(time.time() - letzteMail - mailPause * 60))))
                              
                if stufe > 3:      
                        stufe = 3 # geht nicht höher
                        

                # Statusmeldung ausgeben
                print('%s: durchschnittlich %s Kreise, %s. Meckerstufe' % (formatierteZeit(), circlesDurchschnitt, stufe)) #Statusmeldung
                time.sleep(10) # Bremsen

                if stufe > letzteStufe: 
                        print('%s: Höhere Meckerstufe' % (formatierteZeit()))
                        
                        letzteStufe = stufe #update, damit nächster Sprung korrekt festgestellt wird
                        
                        print('%s: Verbindung zum ftp-Server aufbauen' % (formatierteZeit()))
                        
                        fileName = ('dishtracker%s.png' %(formatierteZeit()))
                        print('%s: Schreibe File %s' %(formatierteZeit(), fileName))
                        
                        try:
                                #Prepare FTP upload
                                session = ftplib.FTP('www.oliverheidorn.de', ftpUser, ftpPwd[18:26])
                                picUpload = open('/home/pi/Pictures/dishtracker.png', 'rb')
                                session.storbinary('STOR /muddi/%s' %(fileName), picUpload)
                                picUpload.close()
                                session.quit()
                                print('%s: FTP hochladen OK' % (formatierteZeit()))
                        except:
                                print('%s: FTP hochladen fehlgeschlagen' % (formatierteZeit()))

                        for strTo in recipients:

                                # Zuweisen der Auswahltexte nach Zufall 
                                poebelAuswahl = poebelText[stufe-1][random.randint(0, len(poebelText[stufe-1])-1)]
                                sublineAuswahl = sublineText[random.randint(0, len(sublineText)-1)]
                                
                                # Create the root message and fill in the from, to, and subject headers
                                msgRoot = MIMEMultipart('related')
                                msgRoot['Subject'] = (betreffText[stufe-1] % (circlesAnzahl))
                                msgRoot['From'] = strFrom
                                msgRoot['To'] = strTo
                                msgRoot.preamble = 'This is a multi-part message in MIME format.'

                                # Encapsulate the plain and HTML versions of the message body in an
                                # 'alternative' part, so message agents can decide which they want to display.
                                msgAlternative = MIMEMultipart('alternative')
                                msgRoot.attach(msgAlternative)

                                msgText = MIMEText('Das ist eine M.U.D.D.I-Warnmail. Leider kannst du die Bilder nicht sehen. Aber lass dir versichert sein: es sieht grauslig aus. Also geh mal in die Kueche und raeum den Kram in die Maschine.')
                                msgAlternative.attach(msgText)

                                # We reference the image in the IMG SRC attribute by the ID we give it below
                                htmlMessage = mailConstruct(poebelAuswahl, fileName, sublineAuswahl)

                                msgText = MIMEText(htmlMessage, 'html', "utf-8")
                                msgAlternative.attach(msgText)

                                # This example assumes the image is in the current directory
                                #fp = open('/home/pi/Pictures/dishtracker.png', 'rb')
                                #msgImage = MIMEImage(fp.read())
                                #fp.close()

                                # Define the image's ID as referenced above
                                #msgImage.add_header('Content-ID', '<image1>')
                                #msgRoot.attach(msgImage)

                                # Send the email (this example assumes SMTP authentication is required)

                                print('%s: Verbindung zum Mailserver aufbauen' % (formatierteZeit()))
                                try:
                                        server = smtplib.SMTP('smtp.gmail.com', 587)
                                        server.starttls()
                                        server.login(strFrom, mailPwd)
                                        server.sendmail(strFrom, strTo, msgRoot.as_string())
                                        server.quit()
                                        print('%s: Mail gesendet' % (formatierteZeit()))
                                        letzteMail = time.time() # Update Mailversand
                                except:
                                        print('%s: Fehler beim Mailversand' % (formatierteZeit()))
                                        
                elif stufe < letzteStufe:
                        
                        #Test: Wenn die Anzahl der runden Formen so weit abnimmt, dass die nächste Meldestufe
                        #unterschritten wird, dann wird die circlesSumme gelöscht und die Meldestufe auf 0 gesetzt

                        print('%s: Niedrigere Warnstufe' % (formatierteZeit()))
                        letzteStufe = stufe
                        stufe = 0
                        del circlesSumme[:]
                        circlesSumme = [0]* circlesMessungen #Sonst kommen wir mit der Statistik und Glättung durcheinander
                        

                
        else:
                                        #Freitags wird geleert
                if datetime.datetime.today().weekday()== 5 and recipients is not None: #Muss Samstag Nacht stattfinden, sonst lscht er Freitags morgens
                        del recipients[:]
                
                #Stage zurcksetzen
                if betriebsMessage == False:
                        print('Kollege macht Pause. Bis später.')
                        betriebsMessage = True


                
                pass

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()

