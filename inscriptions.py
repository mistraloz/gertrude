# -*- coding: cp1252 -*-

import os, datetime, xml.dom.minidom, cStringIO
import wx, wx.lib.scrolledpanel, wx.html
from common import *
from planning import GPanel
from Controls import *
from cotisations import Cotisation, CotisationException

def ParseHtml(filename, context):
    locals().update(context.__dict__)
    data = file(filename, 'r').read()

    # remplacement des <if>
    while 1:
        start = data.find('<if ')
        if start == -1:
            break
        end = data.find('</if>', start) + 5
        text = data[start:end]
        dom = xml.dom.minidom.parseString(text[:text.index('>')+1] + '</if>')
        test = dom.getElementsByTagName('if')[0].getAttribute('value')
        if eval(test):
            replacement = text[text.index('>')+1:-5]
        else:
            replacement = ''
        data = data.replace(text, replacement)
        
    # remplacement des <var>
    while 1:
        start = data.find('<var ')
        if start == -1:
            break
        end = data.find('/>', start) + 2
        text = data[start:end]
        dom = xml.dom.minidom.parseString(text)
        replacement = eval(dom.getElementsByTagName('var')[0].getAttribute('value'))
        if type(replacement) == datetime.date:
            replacement = datestr(replacement)
        elif type(replacement) != str and type(replacement) != unicode:
            replacement = str(replacement)
        data = data.replace(text, replacement)

    return data

class ContextPanel(wx.Panel):
    def __init__(self, parent, creche):
        self.parent = parent
        self.creche = creche
        wx.Panel.__init__(self, parent)
        self.periodechoice = wx.Choice(self, -1, pos=(10, 10), size=(150, 30))
        self.Bind(wx.EVT_CHOICE, self.EvtPeriodeChoice, self.periodechoice)
        self.html_window = wx.html.HtmlWindow(self, pos=(10, 50), style=wx.SUNKEN_BORDER)
        self.Bind(wx.EVT_SIZE, self.OnResize)
    
    def SetInscrit(self, inscrit):
        self.inscrit = inscrit
        self.UpdateContents()
    
    def UpdateContents(self):
        if self.inscrit and self.inscrit.inscriptions[0].debut:
            self.periodechoice.Clear()   
            self.periodes = self.GetPeriodes()
            for p in self.periodes:
                self.periodechoice.Append(datestr(p[0]) + ' - ' + datestr(p[1]))
            if len(self.periodes) > 1:
                self.periodechoice.Enable()
            else:
                self.periodechoice.Disable()
                
            self.periode = self.periodes[-1]
            self.periodechoice.SetSelection(self.periodechoice.GetCount() - 1)
            self.UpdatePage()
        else:
            self.periodechoice.Clear()
            self.periodechoice.Disable()
       
    def EvtPeriodeChoice(self, evt):
        ctrl = evt.GetEventObject()
        self.periode = self.periodes[ctrl.GetSelection()]
        self.UpdatePage()
            
    def OnResize(self, evt):
        w = evt.GetSize().GetWidth() ; h = evt.GetSize().GetHeight()
        self.html_window.SetSize((w-20, h-60))
    
class ContratPanel(ContextPanel):
    def __init__(self, parent, creche):
        ContextPanel.__init__(self, parent, creche)

    def GetPeriodes(self):
        return [(inscription.debut, inscription.fin) for inscription in self.inscrit.inscriptions]

    def UpdatePage(self):
        if self.inscrit is None:
            self.html = '<html><body>Aucun inscrit s&eacute;lectionn&eacute; !</body></html>'
            self.periodechoice.Disable()
        else:
            try:
                context = Cotisation(self.creche, self.inscrit, self.periode)
                if context.mode_garde == 0:
                    self.html = ParseHtml("./templates/contrat_accueil_creche.html", context)
                else:
                    self.html = ParseHtml("./templates/contrat_accueil_creche.html", context)
            except CotisationException, e:
                error = '<br>'.join(e.errors)               
                self.html = u"<html><body><b>Le contrat d'accueil de l'enfant ne peut �tre �dit&eacute; pour la (les) raison(s) suivante(s) :</b><br>" + error + "</body></html>"
        
        self.html_window.SetPage(self.html)
        
class ForfaitPanel(ContextPanel):
    def __init__(self, parent, creche):
        ContextPanel.__init__(self, parent, creche)
        
    def GetPeriodes(self):
        periodes = []
        for inscription in self.inscrit.inscriptions:
            separators = self.__get_separators(inscription.debut, inscription.fin)
            separators.sort()
            all_periodes = [(separators[i], separators[i+1] - datetime.timedelta(1)) for i in range(len(separators)-1)]
            previous_context = None
            previous_periode = None
            for periode in all_periodes:
                try:
                    context = Cotisation(self.creche, self.inscrit, periode)                    
                    if not previous_periode or context != previous_context:
                        periodes.append(periode)           
                        previous_periode = periode
                        previous_context = context
                    else:
                        periodes[-1] = (previous_periode[0], periode[1])
                except CotisationException, e:
                    periodes.append(periode)           
                    previous_periode = periode
                    previous_context = None
        return periodes

    def __get_separators(self, debut, fin):
        if debut is None:
            return []
            
        if fin is None:
            if today.month < 9:
                fin = datetime.date(day=1, month=9, year=datetime.date.today().year)
            else:
                fin = datetime.date(day=1, month=9, year=datetime.date.today().year + 1)
        else:
            fin = fin + datetime.timedelta(1)

        separators = [debut, fin]
            
        def addseparator(separator, end=0):
            if separator is None:
                return
            if end == 1:
                separator = separator + datetime.timedelta(1)
            if separator >= debut and separator <= fin and not separator in separators:
                separators.append(separator)

        for parent in [self.inscrit.papa, self.inscrit.maman]:
            for revenu in parent.revenus:
                addseparator(revenu.debut)
                addseparator(revenu.fin, 1)
        for frere_soeur in self.inscrit.freres_soeurs:
            addseparator(frere_soeur.naissance)
            addseparator(frere_soeur.entree)
            addseparator(frere_soeur.sortie, 1)
        for bareme in self.creche.baremes_caf:
            addseparator(bareme.debut)
            addseparator(bareme.fin, 1)
        for year in range(debut.year, fin.year):
            addseparator(datetime.date(day=1, month=9, year=year))
            
        return separators

    def UpdatePage(self):      
        if self.inscrit is None:
            self.html = '<html><body>Aucun inscrit s&eacute;lectionn&eacute; !</body></html>'
        else:
            try:
                context = Cotisation(self.creche, self.inscrit, self.periode)
                if context.mode_garde == 0:
                    self.html = ParseHtml("./templates/frais_de_garde.html", context)
                else:
                    self.html = ParseHtml("./templates/frais_de_garde_hg.html", context)
            except CotisationException, e:
                error = '<br>'.join(e.errors)
                self.html = u"<html><body><b>Les frais de garde mensuels ne peuvent �tre calcul&eacute;s pour la (les) raison(s) suivante(s) :</b><br>" + error  + "</body></html>"
                
        self.html_window.SetPage(self.html)

class WeekWindow(wx.Window):
    pxLigne = 30
    pxColonnes = [ -1, 100, 150, 250 ]
    EVT_CHANGE = 1
    
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1, size=(self.pxColonnes[-1] + 71, self.pxLigne * 5 + 31))
        self.tabwindow = wx.Window(self, pos=(60, 30), size=(self.pxColonnes[-1]+1, self.pxLigne * 5 + 1), style = wx.SUNKEN_BORDER)
        self.tabwindow.Bind(wx.EVT_PAINT, self.OnTabPaint)
        self.curStartX = None
        self.semaine_type = None
        self.on_change_handler = None
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        
    def Bind(self, event, handler):
        if event == self.EVT_CHANGE:
            self.on_change_handler = handler
        else:
            wx.Window.Bind(self, event, handler)
        
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.PrepareDC(dc)
        dc.SetPen(wx.GREY_PEN)
        dc.SetTextForeground('BLACK')
        font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL) # TODO statictext
        dc.SetFont(font)
        dc.DrawText('Matin', self.pxColonnes[0] + 90, 8)
        dc.DrawText('Midi', self.pxColonnes[1] + 75, 8)
        dc.DrawText(u'Apr�s-midi', self.pxColonnes[2] + 80, 8)
        
        for i in range(5):
            dc.DrawText(days[i], 0, i * self.pxLigne + 37)
            
    def OnTabPaint(self, event):
        dc = wx.PaintDC(self.tabwindow)
        self.tabwindow.PrepareDC(dc)
        if self.semaine_type:
            self.DoDrawing(dc)

    def DrawDay(self, dc, ligne, presence):
        dc.SetPen(wx.TRANSPARENT_PEN)
        for i in range(3):
            if presence[i]:
                dc.SetBrush(wx.Brush(wx.Color(5, 203, 28)))
            else:
                dc.SetBrush(wx.WHITE_BRUSH)
            dc.DrawRectangle(self.pxColonnes[i]+1, ligne * self.pxLigne, self.pxColonnes[i+1]-self.pxColonnes[i]-1, self.pxLigne - 1)

    def DoDrawing(self, dc):
        dc.BeginDrawing()
        dc.SetPen(wx.GREY_PEN)
        for i in range(5):
            dc.DrawLine(0, (i + 1) * self.pxLigne - 1, self.pxColonnes[-1], (i + 1) * self.pxLigne - 1)
        for i in self.pxColonnes[1:]:
            dc.DrawLine(i, 0, i, self.pxLigne * 5 + 1)
        if self.semaine_type:
            for i in range(5):
                self.DrawDay(dc, i, self.semaine_type[i])
        dc.EndDrawing()

    def __get_pos(self, x, y):
        posY = int(y / self.pxLigne)
        for i in range(1, 4):
            if x < self.pxColonnes[i]:
                posX = i - 1
                return posX, posY

    def OnLeftButtonEvent(self, event):
        x = event.GetX()
        y = event.GetY()

        if event.LeftDown():
            self.curStartX, self.curStartY = self.__get_pos(x, y)
            
        if (event.LeftDown() or event.Dragging()) and self.curStartX is not None:
            self.curEndX, self.curEndY = self.__get_pos(x, y)

            if self.curEndY == self.curStartY:
                dc = wx.ClientDC(self.tabwindow)
                self.tabwindow.PrepareDC(dc)
                start, end = min(self.curStartX, self.curEndX), max(self.curStartX, self.curEndX)
                valeur_selection = not self.semaine_type[self.curStartY][self.curStartX]                  
                self.jour_tmp = 3 * [0]
                self.jour_tmp[:] = self.semaine_type[self.curStartY]
                for i in range(start, end+1):
                    self.jour_tmp[i] = valeur_selection
                self.DrawDay(dc, self.curStartY, self.jour_tmp)
                
        elif event.LeftUp() and self.curStartX is not None:
                if self.jour_tmp != [0, 1, 0]:
                    self.semaine_type[self.curStartY] = self.jour_tmp
                else:
                    self.semaine_type[self.curStartY] = [0, 0, 0]
                    dc = wx.ClientDC(self.tabwindow)
                    self.tabwindow.PrepareDC(dc)
                    self.DrawDay(dc, self.curStartY, self.semaine_type[self.curStartY])
                self.curStartX = None
                self.OnChange(self.semaine_type)
                
    def SetSemaine(self, semaine_type):
        self.semaine_type = semaine_type
        if semaine_type:
            self.tabwindow.SetBackgroundColour(wx.WHITE)
            self.tabwindow.Bind(wx.EVT_LEFT_DOWN, self.OnLeftButtonEvent)
            self.tabwindow.Bind(wx.EVT_LEFT_UP, self.OnLeftButtonEvent)
            self.tabwindow.Bind(wx.EVT_MOTION, self.OnLeftButtonEvent)
            self.tabwindow.SetCursor(wx.StockCursor(wx.CURSOR_PENCIL))
        else:
            self.tabwindow.SetBackgroundColour(wx.LIGHT_GREY)
            for evt in [wx.EVT_LEFT_DOWN, wx.EVT_LEFT_UP, wx.EVT_MOTION]:
                self.tabwindow.Unbind(evt)
            self.tabwindow.SetCursor(wx.STANDARD_CURSOR)
        self.tabwindow.Refresh()
        
    def OnChange(self, value):
        if self.on_change_handler:
            self.on_change_handler(value)
            
wildcard = "PNG (*.png)|*.png|"     \
           "BMP (*.pmp)|*.bmp|"     \
           "All files (*.*)|*.*"
           
class InscriptionsTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        self.inscrit = None
    
    def SetInscrit(self, inscrit):
        self.inscrit = inscrit
        for ctrl in self.ctrls:
            ctrl.SetInstance(inscrit)

class IdentitePanel(InscriptionsTab):
    def __init__(self, parent):
        InscriptionsTab.__init__(self, parent)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2 = wx.FlexGridSizer(4, 2, 5, 5)
        ctrl = AutoTextCtrl(self, None, 'prenom')
        self.Bind(wx.EVT_TEXT, self.EvtChangementPrenom, ctrl)
        sizer2.AddMany([(wx.StaticText(self, -1, u'Pr�nom :'), 0, wx.ALIGN_CENTER_VERTICAL), ctrl])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Nom :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoTextCtrl(self, None, 'nom')])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Date de naissance :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoDateCtrl(self, None, 'naissance')])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Adresse :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoTextCtrl(self, None, 'adresse')])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Code Postal :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoNumericCtrl(self, None, 'code_postal', min=0, precision=0)])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Ville :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoTextCtrl(self, None, 'ville')])
        sizer2.AddMany([(wx.StaticText(self, -1, 'Date de marche :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoDateCtrl(self, None, 'marche')])
        sizer1.Add(sizer2)

        self.photo = wx.BitmapButton(self, 30, pos=(280, 40), size=(100, 150))
        self.nophoto = wx.Bitmap('./bitmaps/essai.png')
        self.photo.SetBitmapLabel(self.nophoto)
        self.Bind(wx.EVT_BUTTON, self.OnPhotoButton, self.photo)
        sizer1.Add(self.photo)
        
        self.fratries_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Fr�res et soeurs'), wx.VERTICAL)
        self.nouveau_frere = wx.Button(self, -1, u'Nouveau fr�re ou nouvelle soeur')
        self.nouveau_frere.Disable()
        self.fratries_sizer.Add(self.nouveau_frere, 0, wx.EXPAND)
        self.Bind(wx.EVT_BUTTON, self.EvtNouveauFrere, self.nouveau_frere)
        
        self.sizer.Add(sizer1)
        self.sizer.Add(self.fratries_sizer)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        
    def __add_fratrie(self, index):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.AddMany([(wx.StaticText(self, -1, u'Pr�nom :'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoTextCtrl(self, self.inscrit, 'freres_soeurs[%d].prenom' % index), 0, wx.ALIGN_CENTER_VERTICAL)])
        sizer.AddMany([(wx.StaticText(self, -1, 'Naissance :'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoDateCtrl(self, self.inscrit, 'freres_soeurs[%d].naissance' % index), 0, wx.ALIGN_CENTER_VERTICAL)])
        sizer.AddMany([(wx.StaticText(self, -1, u'En cr�che du'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoDateCtrl(self, self.inscrit, 'freres_soeurs[%d].entree' % index), 0, wx.ALIGN_CENTER_VERTICAL)])
        sizer.AddMany([(wx.StaticText(self, -1, 'au'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoDateCtrl(self, self.inscrit, 'freres_soeurs[%d].sortie' % index), 0, wx.ALIGN_CENTER_VERTICAL)])
        delbutton = wx.Button(self, -1, 'X')
        delbutton.index = index
        sizer.Add(delbutton)
        self.Bind(wx.EVT_BUTTON, self.EvtSuppressionFrere, delbutton)
        self.fratries_sizer.Add(sizer)
        self.sizer.Layout()
    
    def EvtChangementPrenom(self, event):
        event.GetEventObject().onText(event)
        self.parent.EvtChangementPrenom(event)
        
    def EvtNouveauFrere(self, event):
        self.inscrit.freres_soeurs.append(Frere_Soeur(self.inscrit))
        self.__add_fratrie(len(self.inscrit.freres_soeurs) - 1)
        self.sizer.Layout()
        
    def EvtSuppressionFrere(self, event):
        index = event.GetEventObject().index
        sizer = self.fratries_sizer.GetItem(len(self.inscrit.freres_soeurs))
        sizer.DeleteWindows()
        self.fratries_sizer.Detach(len(self.inscrit.freres_soeurs))
        del self.inscrit.freres_soeurs[index]
        self.sizer.Layout()
        
    def SetInscrit(self, inscrit):
        old = new = 0
        if self.inscrit:
            old = len(self.inscrit.freres_soeurs)
        if inscrit:
            new = len(inscrit.freres_soeurs)
        if old > new:
            for i in range(old, new, -1):
                self.fratries_sizer.GetItem(i).DeleteWindows()
                self.fratries_sizer.Detach(i)

        InscriptionsTab.SetInscrit(self, inscrit)
        self.nouveau_frere.Enable(self.inscrit!=None)
        
        if new > old:
            for i in range(old, new):
                self.__add_fratrie(i)

        self.sizer.Layout()
        
        if inscrit:
            self.photo.Enable()
            if inscrit.photo:
                img = wx.ImageFromData(80, 130, inscrit.photo)
                bmp = wx.BitmapFromImage(img)
            else:
                bmp = self.nophoto
        else:
            self.photo.Disable()
            bmp = self.nophoto
            
        self.photo.SetBitmapLabel(bmp)
        self.photo.Refresh()
                
    def OnPhotoButton(self, event):
        if self.inscrit:
            if self.inscrit.prenom and self.inscrit.nom:
                old_path = os.getcwd()
                dlg = wx.FileDialog(self, message="Choisir un fichier", defaultDir=os.getcwd(),
                                    defaultFile="", wildcard=wildcard, style=wx.OPEN | wx.CHANGE_DIR)
                response = dlg.ShowModal()
                os.chdir(old_path)
                if response == wx.ID_OK:
                    img = wx.Image(dlg.GetPath())
                    #if img.GetWidth() > 80 or img.GetHeight() > 130:
                    img.Rescale(80, 130)
                    
                    #img.SaveFile(cStringIO.StringIO(data), wx.BITMAP_TYPE_PNG )
                    #bmp = wx.BitmapFromImage(wx.ImageFromStream(cStringIO.StringIO(data)))
                    self.photo.SetBitmapLabel(wx.BitmapFromImage(img))
                    self.photo.Refresh()
                    self.inscrit.photo = img.GetData()
                dlg.Destroy()
            else:
                dlg = wx.MessageDialog(self, 
                                       u"Il faut d'abord remplir le pr�nom et le nom de l'enfant",
                                       'Message',
                                       wxICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()

class ParentsPanel(InscriptionsTab):
    def __init__(self, parent, profil):
        InscriptionsTab.__init__(self, parent)
        self.regimes_choices = []
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        for parent in ['papa', 'maman']:
            sizer1 = wx.StaticBoxSizer(wx.StaticBox(self, -1, parent.capitalize()), wx.VERTICAL)
            sizer11 = wx.BoxSizer(wx.VERTICAL)
            sizer1.Add(sizer11)
            sizer2 = wx.FlexGridSizer(4, 2, 5, 5)
            sizer2.AddMany([(wx.StaticText(self, -1, u'Pr�nom :'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoTextCtrl(self, None, '%s.prenom' % parent), 0, wx.EXPAND)])
            sizer2.AddMany([(wx.StaticText(self, -1, 'Nom :'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoTextCtrl(self, None, '%s.nom' % parent), 0, wx.EXPAND)])
            sizer3 = wx.BoxSizer(wx.HORIZONTAL)
            sizer3.AddMany([AutoPhoneCtrl(self, None, '%s.telephone_domicile' % parent), AutoTextCtrl(self, None, '%s.telephone_domicile_notes' % parent)])        
            sizer2.AddMany([(wx.StaticText(self, -1, u'T�l�phone domicile :'), 0, wx.ALIGN_CENTER_VERTICAL), sizer3])
            sizer3 = wx.BoxSizer(wx.HORIZONTAL)
            sizer3.AddMany([AutoPhoneCtrl(self, None, '%s.telephone_portable' % parent), AutoTextCtrl(self, None, '%s.telephone_portable_notes' % parent)])        
            sizer2.AddMany([(wx.StaticText(self, -1, u'T�l�phone portable :'), 0, wx.ALIGN_CENTER_VERTICAL), sizer3])
            sizer3 = wx.BoxSizer(wx.HORIZONTAL)
            sizer3.AddMany([AutoPhoneCtrl(self, None, '%s.telephone_travail' % parent), AutoTextCtrl(self, None, '%s.telephone_travail_notes' % parent)])        
            sizer2.AddMany([(wx.StaticText(self, -1, u'T�l�phone travail :'), 0, wx.ALIGN_CENTER_VERTICAL), sizer3])
            sizer2.AddMany([(wx.StaticText(self, -1, 'E-mail :'), 0, wx.ALIGN_CENTER_VERTICAL), (AutoTextCtrl(self, None, '%s.email' % parent), 0, wx.EXPAND)])           
            sizer11.Add(sizer2)
            
	    if profil & PROFIL_TRESORIER:
                panel = PeriodePanel(self)
                sizer4 = wx.BoxSizer(wx.VERTICAL)
                sizer4.Add(PeriodeChoice(panel, None, '%s.revenus' % parent, eval('self.nouveau_revenu_%s' % parent)))
                sizer4.AddMany([(wx.StaticText(panel, -1, 'Revenus annuels bruts :'), 0, wx.ALIGN_CENTER_VERTICAL), AutoNumericCtrl(panel, None, '%s.revenus[self.parent.periode].revenu' % parent, precision=2)])
                sizer4.Add(AutoCheckBox(panel, None, '%s.revenus[self.parent.periode].chomage' % parent, u'Ch�mage'))
                choice = AutoChoiceCtrl(panel, None, '%s.revenus[self.parent.periode].regime' % parent)
                self.regimes_choices.append(choice)
                for i, regime in enumerate([u'Pas de s�lection', u'R�gime g�n�ral', u'R�gime de la fonction publique', u'R�gime MSA', u'R�gime EDF-GDF', u'R�gime RATP', u'R�gime P�che maritime', u'R�gime Marins du Commerce']):
                    choice.Append(regime, i)
                panel.Bind(wx.EVT_CHOICE, self.onRegimeChoice, choice)
                sizer4.AddMany([wx.StaticText(panel, -1, u"R�gime d'appartenance :"), choice])           
                panel.SetSizer(sizer4)           
                sizer11.Add(panel)

            sizer.Add(sizer1)

        self.SetSizer(sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()

    def nouveau_revenu_papa(self):
        return Revenu(self.inscrit.papa)
    
    def nouveau_revenu_maman(self):
        return Revenu(self.inscrit.maman)
   
    def onRegimeChoice(self, event):
        obj = event.GetEventObject()
        if obj.GetSelection() != 0:
            for choice in self.regimes_choices:
                if choice != obj:
                    choice.SetValue(0)
        event.Skip()

class ModeAccueilPanel(InscriptionsTab):
    def __init__(self, parent):
        InscriptionsTab.__init__(self, parent)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(PeriodeChoice(self, None, 'inscriptions', self.nouvelleInscription))
        sizer.Add(AutoRadioBox(self, None, 'inscriptions[self.parent.periode].mode', "Mode d'accueil", [u'Cr�che', 'Halte-garderie']))
        sizer.AddMany([(wx.StaticText(self, -1, u"Date de fin de la p�riode d'essai :"), 0, wx.ALIGN_CENTER_VERTICAL), AutoDateCtrl(self, None, 'inscriptions[self.parent.periode].fin_periode_essai')])
        sizer1 = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Semaine type'), wx.HORIZONTAL)
        sizer.Add(sizer1)
        self.week_ctrl = WeekWindow(self)
        self.week_ctrl.Bind(WeekWindow.EVT_CHANGE, self.OnPeriodeChange)
        sizer1.Add(self.week_ctrl)
        bmp = wx.Bitmap("./bitmaps/icone_plein_temps.png", wx.BITMAP_TYPE_PNG)
        btn = wx.BitmapButton(self, -1, bmp)
        sizer1.Add(btn)
        self.Bind(wx.EVT_BUTTON, self.EvtButton55e, btn)
        self.SetSizer(sizer)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        
    def nouvelleInscription(self): # TODO les autres pareil ...
        return Inscription(self.inscrit)
    
    def SetInscrit(self, inscrit):
        InscriptionsTab.SetInscrit(self, inscrit)
        if inscrit: # TODO week_ctrl comme les autres ctrls ?
            self.week_ctrl.SetSemaine(inscrit.inscriptions[self.periode].periode_reference)
        else:
            self.week_ctrl.SetSemaine(None)
    
    def EvtButton55e(self, event):
        if self.inscrit.inscriptions[self.periode].periode_reference != 5 * [[1, 1, 1]]:
            self.inscrit.inscriptions[self.periode].periode_reference = 5 * [[1, 1, 1]]
            self.week_ctrl.SetSemaine(self.inscrit.inscriptions[self.periode].periode_reference)
    
    def OnPeriodeChange(self, periode):
        self.inscrit.inscriptions[self.periode].periode_reference = periode

    def UpdateContents(self):
        InscriptionsTab.UpdateContents(self)
        if self.inscrit:
            self.week_ctrl.SetSemaine(self.inscrit.inscriptions[self.periode].periode_reference)
        else:
            self.week_ctrl.SetSemaine(None)
    
class InscriptionsNotebook(wx.Notebook):
    def __init__(self, parent, profil, creche, *args, **kwargs):
        wx.Notebook.__init__(self, parent, style=wx.LB_DEFAULT, *args, **kwargs)      
        self.parent = parent
        self.profil = profil
        self.inscrit = None

        self.AddPage(IdentitePanel(self), u'Identit�')
        self.AddPage(ParentsPanel(self, profil), 'Parents')
        self.AddPage(ModeAccueilPanel(self), "Mode d'accueil")

        if self.profil & PROFIL_TRESORIER:
            self.contrat_panel = ContratPanel(self, creche)
            self.forfait_panel = ForfaitPanel(self, creche)
            self.AddPage(self.contrat_panel, 'Contrat PSU')
            self.AddPage(self.forfait_panel, 'Frais de garde mensuels')
        else:
            self.contrat_panel = self.forfait_panel = None

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)  
            
    def EvtChangementPrenom(self, event):
        self.parent.ChangePrenom(self.inscrit)

    def OnPageChanged(self, event):
        page = self.GetPage(event.GetSelection())
        page.UpdateContents()
        event.Skip()

    def SetInscrit(self, inscrit):
        self.inscrit = inscrit
        for i in range(self.GetPageCount()):
            page = self.GetPage(i)
            page.SetInscrit(inscrit)
            
    def UpdateContents(self):
        page = self.GetCurrentPage()
        page.Update()

#                if self.inscrit.photo:
#                    bmp = wxBitmap(self.inscrit.photo)
#                else:
#                    bmp = wxBitmap("./bitmaps/essai.png", wx.BITMAP_TYPE_PNG)
#    
#                self.photo.SetBitmapLabel(bmp)
#                self.photo.Refresh()
            
class InscriptionsPanel(GPanel):
    def __init__(self, parent, profil, creche, inscrits):
        GPanel.__init__(self, parent, "Inscriptions")

        self.profil = profil
        self.creche = creche
        self.inscrits = inscrits

        # Le control pour la selection du bebe
	sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.choice = wx.Choice(self, -1)
        self.Bind(wx.EVT_CHOICE, self.EvtInscritChoice, self.choice)
        self.delbutton = wx.Button(self, -1, 'Suppression')
        self.Bind(wx.EVT_BUTTON, self.EvtInscritDelButton, self.delbutton)
        sizer.AddMany([(self.choice, 1, wx.EXPAND), (self.delbutton, 0, wx.RIGHT)])
	self.sizer.Add(sizer, 0, wx.EXPAND)
        # le notebook pour la fiche d'inscription
        self.notebook = InscriptionsNotebook(self, profil, creche)
	self.sizer.Add(self.notebook, 1, wx.EXPAND)
        self.InitInscrits()

    def UpdateContents(self):
        self.InitInscrits()

    def InitInscrits(self, selected=None):
        self.choice.Clear()
        # Ceux qui sont presents
        for inscrit in self.inscrits:
            if inscrit.getInscription(datetime.date.today()) != None:
                self.choice.Append(GetInscritId(inscrit, self.inscrits), inscrit)
        self.choice.Append(150 * '-', None)
        self.choice.Append('Nouvelle inscription', None)
        self.choice.Append(150 * '-', None)
        # Les autres
        for inscrit in self.inscrits:
            if inscrit.getInscription(datetime.date.today()) == None:
                self.choice.Append(GetInscritId(inscrit, self.inscrits), inscrit)

        if len(self.inscrits) > 0 and selected != None and selected in self.inscrits:
            self.SelectInscrit(selected)
        elif (len(self.inscrits) > 0):
            self.SelectInscrit(self.choice.GetClientData(0))
        else:
            self.SelectInscrit(None)
        
    def EvtInscritChoice(self, evt):
        ctrl = evt.GetEventObject()
        selected = ctrl.GetSelection()
        inscrit = ctrl.GetClientData(selected)
        if inscrit:
            self.delbutton.Enable()
            self.SelectInscrit(inscrit)
        else:
            ctrl.SetStringSelection('Nouvelle inscription')
            if self.notebook.inscrit is None or GetInscritId(self.notebook.inscrit, self.inscrits) != '':
                inscrit = Inscrit()
                self.inscrits.append(inscrit)
                self.notebook.SetInscrit(inscrit)
                self.notebook.SetSelection(0) # Selectionne la page identite
                self.delbutton.Disable()

    def SelectInscrit(self, inscrit):
        if inscrit:
            for i in range(self.choice.GetCount()):
                if self.choice.GetClientData(i) == inscrit:
                    self.choice.SetSelection(i)
                    break
        else:
            self.choice.SetSelection(-1)
        self.notebook.SetInscrit(inscrit)
            
    def EvtInscritDelButton(self, evt):
        selected = self.choice.GetSelection()
        inscrit = self.choice.GetClientData(selected)
        if inscrit:
            dlg = wx.MessageDialog(self,
                                   'Cette inscription va �tre supprim�e, �tes-vous s�r de vouloir continuer ?',
                                   'Confirmation',
                                   wx.YES_NO | wx.NO_DEFAULT | wx.ICON_EXCLAMATION )
            if dlg.ShowModal() == wx.ID_YES:
                inscrit.delete()
                self.inscrits.remove(inscrit)
                self.choice.Delete(selected)
                self.choice.SetSelection(-1)
                self.notebook.SetInscrit(None)
                self.delbutton.Disable()
            dlg.Destroy()
        
    def ChangePrenom(self, inscrit):
        inscritId = GetInscritId(inscrit, self.inscrits)
        if self.choice.GetClientData(self.choice.GetSelection()) is None:
            if inscritId != '':
                self.choice.Insert(inscritId, 0, inscrit)
                self.delbutton.Enable()
        else:
            self.choice.SetString(self.choice.GetSelection(), inscritId)
        self.choice.SetStringSelection(inscritId)
                                
