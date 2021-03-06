# -*- coding: utf-8 -*-

##    This file is part of Gertrude.
##
##    Gertrude is free software; you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation; either version 3 of the License, or
##    (at your option) any later version.
##
##    Gertrude is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with Gertrude; if not, see <http://www.gnu.org/licenses/>.

import __builtin__
import os.path
import sys
import string
import datetime
import wx, wx.lib.scrolledpanel, wx.html, wx.grid, wx.lib.expando
from constants import *
from functions import *
from controls import *
from ooffice import *
from doc_planning import PlanningModifications
from doc_coordonnees_parents import CoordonneesModifications
from doc_etats_trimestriels import EtatsTrimestrielsModifications
from doc_releve_siej import ReleveSIEJModifications
from doc_releve_detaille import ReleveDetailleModifications
from doc_planning_detaille import PlanningDetailleModifications
from doc_etat_presences import EtatsPresenceModifications
from doc_etat_places import EtatPlacesModifications
from doc_etats_inscriptions import EtatsInscriptionsModifications
from doc_rapport_frequentation import RapportFrequentationModifications
from doc_synthese_financiere import SyntheseFinanciereModifications
from doc_releve_salaries import ReleveSalariesModifications
from doc_etat_presence_mensuel import EtatPresenceMensuelModifications
from doc_commande_repas import CommandeRepasModifications
from facture import Facture
from planning import *
from sqlobjects import Day

class SitesPlanningPanel(PlanningWidget):
    def UpdateContents(self):          
        first_monday = GetFirstMonday()
        lines = []
        for week_day in range(7):
            date = first_monday + datetime.timedelta(self.semaine * 7 + week_day)
            if date in creche.jours_fermeture:
                continue
            
            day_lines = {}
            if len(creche.sites) > 1:
                lines.append(days[week_day])
                for site in creche.sites:
                    line = Summary(site.nom)
                    for i in range(int(creche.ouverture*60/BASE_GRANULARITY), int(creche.fermeture*60/BASE_GRANULARITY)):
                        line[i][0] = site.capacite
                    day_lines[site] = line
                    lines.append(line)
            else:
                site_line = Summary(days[week_day])
                for i in range(int(creche.ouverture*60/BASE_GRANULARITY), int(creche.fermeture*60/BASE_GRANULARITY)):
                    site_line[i][0] = 0
                for start, end, value in creche.tranches_capacite[week_day].activites:
                    for i in range(start, end):
                        site_line[i][0] = value
                lines.append(site_line)
            
            for inscrit in creche.inscrits:
                if date not in inscrit.jours_conges:
                    inscription = inscrit.GetInscription(date)
                    if inscription is not None:
                        if date in inscrit.journees:
                            line = inscrit.journees[date]
                        else:
                            line = inscrit.GetJourneeReference(date)
                        if len(creche.sites) > 1:
                            if inscription.site and inscription.site in day_lines:
                                site_line = day_lines[inscription.site]
                            else:
                                continue
                        for start, end, value in line.activites:
                            if value in (0, PREVISIONNEL):
                                for i in range(start, end):
                                    site_line[i][0] -= 1

        self.SetLines(lines)

    def SetData(self, semaine):
        self.semaine = semaine
        self.UpdateContents()
        
class ReservatairesPlanningPanel(PlanningWidget):
    def UpdateContents(self):          
        first_monday = GetFirstMonday()
        lines = []
        for week_day in range(7):
            date = first_monday + datetime.timedelta(self.semaine * 7 + week_day)
            if date in creche.jours_fermeture:
                continue
            
            day_lines = {}
            lines.append(days[week_day])
            places_reservees = 0
            for reservataire in creche.reservataires:
                line = Summary(reservataire.nom)
                for i in range(int(creche.ouverture*60/BASE_GRANULARITY), int(creche.fermeture*60/BASE_GRANULARITY)):
                    line[i][0] = reservataire.places
                day_lines[reservataire] = line
                if reservataire.places:
                    places_reservees += reservataire.places
                lines.append(line)
            line = Summary("[Structure]")
            for i in range(int(creche.ouverture*60/BASE_GRANULARITY), int(creche.fermeture*60/BASE_GRANULARITY)):
                line[i][0] = 0
            for start, end, value in creche.tranches_capacite[week_day].activites:
                for i in range(start, end):
                    line[i][0] = max(0, value)
            day_lines[None] = line
            lines.append(line)
            
            for inscrit in creche.inscrits:
                if date not in inscrit.jours_conges:
                    inscription = inscrit.GetInscription(date)
                    if inscription is not None:
                        line = inscrit.GetJournee(date)
                        if inscription.reservataire and inscription.reservataire in day_lines:
                            reservataire_line = day_lines[inscription.reservataire]
                        else:
                            reservataire_line = None
                        for start, end, value in line.activites:
                            if value in (0, PREVISIONNEL):
                                for i in range(start, end):
                                    day_lines[None][i][0] -= 1
                                    if reservataire_line is not None:
                                        reservataire_line[i][0] -= 1

        self.SetLines(lines)

    def SetData(self, semaine):
        self.semaine = semaine
        self.UpdateContents()

class PlacesDisponiblesTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Les raccourcis pour semaine précédente / suivante
        self.previous_button = wx.Button(self, -1, '<', size=(20,0), style=wx.NO_BORDER)
        self.next_button = wx.Button(self, -1, '>', size=(20,0), style=wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.onPreviousWeek, self.previous_button)
        self.Bind(wx.EVT_BUTTON, self.onNextWeek, self.next_button)
        sizer.Add(self.previous_button, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        sizer.Add(self.next_button, 0, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        
        # La combobox pour la selection de la semaine
        self.week_choice = wx.Choice(self, -1)
        sizer.Add(self.week_choice, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        day = first_monday = GetFirstMonday()
        while day < last_date:
            string = 'Semaine %d (%d %s %d)' % (day.isocalendar()[1], day.day, months[day.month - 1], day.year)
            self.week_choice.Append(string, day)
            day += datetime.timedelta(7)
        delta = datetime.date.today() - first_monday
        semaine = int(delta.days / 7)
        self.week_choice.SetSelection(semaine)
        self.Bind(wx.EVT_CHOICE, self.OnChangeWeek, self.week_choice)
        self.sizer.Add(sizer, 0, wx.EXPAND)
                
        if (config.options & RESERVATAIRES) and len(creche.reservataires) > 0:
            self.planning_panel = ReservatairesPlanningPanel(self, options=DRAW_NUMBERS|NO_ICONS|NO_BOTTOM_LINE|READ_ONLY)
        else:
            self.planning_panel = SitesPlanningPanel(self, options=DRAW_NUMBERS|NO_ICONS|NO_BOTTOM_LINE|READ_ONLY)
        self.planning_panel.SetData(semaine)          
        self.sizer.Add(self.planning_panel, 1, wx.EXPAND)
        self.sizer.Layout()
        self.SetSizer(self.sizer)

    def OnChangeWeek(self, evt=None):   
        week_selection = self.week_choice.GetSelection()
        self.previous_button.Enable(week_selection is not 0)
        self.next_button.Enable(week_selection is not self.week_choice.GetCount() - 1)
        monday = self.week_choice.GetClientData(week_selection)
        self.planning_panel.SetData(week_selection)
        self.sizer.Layout()
        
    def onPreviousWeek(self, evt):
        self.week_choice.SetSelection(self.week_choice.GetSelection() - 1)
        self.OnChangeWeek()
    
    def onNextWeek(self, evt):
        self.week_choice.SetSelection(self.week_choice.GetSelection() + 1)
        self.OnChangeWeek()
        
    def UpdateContents(self):            
        self.OnChangeWeek()


class EtatsPresenceTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.debut_control = DateCtrl(self)
        self.debut_control.SetValue(today)
        wx.EVT_TEXT(self.debut_control, -1, self.onPeriodeChange)
        self.search_sizer.AddMany([(wx.StaticText(self, -1, u'Début :'), 0, wx.ALIGN_CENTER_VERTICAL), (self.debut_control, 0, wx.ALIGN_CENTER_VERTICAL)])
        self.fin_control = DateCtrl(self)
        self.fin_control.SetValue(today)
        wx.EVT_TEXT(self.fin_control, -1, self.onPeriodeChange)
        self.search_sizer.AddMany([(wx.StaticText(self, -1, u'Fin :'), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5), (self.fin_control, 0, wx.ALIGN_CENTER_VERTICAL)])
        self.ordered_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.unordered_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sites_choice = wx.Choice(self)
        self.sites_choice.fill_function = self.FillSites
        self.sites_choice.parameter = "site"
        self.professeurs_choice = wx.Choice(self)
        self.professeurs_choice.fill_function = self.FillProfesseurs
        self.professeurs_choice.parameter = "professeur"
        self.inscrits_choice = wx.Choice(self)
        self.inscrits_choice.fill_function = self.FillInscrits
        self.inscrits_choice.parameter = "inscrit"
        self.unordered_sizer.AddMany([(self.sites_choice, 0, wx.LEFT, 5), (self.professeurs_choice, 0, wx.LEFT, 5), (self.inscrits_choice, 0, wx.LEFT, 5)])
        self.search_sizer.AddMany([(self.ordered_sizer, 0, wx.ALIGN_CENTER_VERTICAL), (self.unordered_sizer, 0, wx.ALIGN_CENTER_VERTICAL)])
        self.sizer.Add(self.search_sizer, 0, wx.ALL|wx.EXPAND, 5)
        self.ordered = []
        self.unordered = [self.sites_choice, self.professeurs_choice, self.inscrits_choice]
        self.debut_value = None
        self.fin_value = None
        
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, wx.ID_OK)
        sizer2.Add(ok, 0)
        export = wx.Button(self, -1, "Export")
        sizer2.Add(export)
        self.sizer.Add(sizer2, 0, wx.ALL, 5)
        
        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(0, 3)
        # self.grid.EnableScrolling(False, False)
        self.grid.SetRowLabelSize(1)
        self.grid.SetColLabelValue(0, "Date")
        self.site_col_displayed = 0
        self.professeur_col_displayed = 0
        self.grid.SetColLabelValue(1, "Inscrit")
        self.grid.SetColLabelValue(2, "Heures")
        self.grid.SetColSize(0, 155)
        self.grid.SetColSize(1, 155)
        self.grid.SetColSize(2, 200)
        self.sizer.Add(self.grid, -1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(self.sizer)
        self.UpdateContents()
        
        self.Bind(wx.EVT_BUTTON, self.onOk, ok)
        self.Bind(wx.EVT_BUTTON, self.onExport, export)
        self.Bind(wx.EVT_CHOICE, self.onChoice, self.sites_choice)
        self.Bind(wx.EVT_CHOICE, self.onChoice, self.professeurs_choice)
        self.Bind(wx.EVT_CHOICE, self.onChoice, self.inscrits_choice)

    def FillSites(self, debut=None, fin=None, inscrit=None, professeur=None):
        if len(creche.sites) < 2:
            self.sites_choice.Show(False)
            return
        
        if debut is None and fin is None and inscrit is None:
            sites = creche.sites
        else:
            sites = set()
            if inscrit:
                inscrits = [inscrit]
            else:
                inscrits = creche.inscrits
            for inscrit in inscrits:
                for inscription in inscrit.GetInscriptions(debut, fin):
                    if inscription.site:
                        sites.add(inscription.site)
        self.sites_choice.Show(True)
        self.sites_choice.Clear()
        self.sites_choice.Append("Tous les sites", None)
        for site in sites:
            self.sites_choice.Append(site.nom, site)
        self.sites_choice.Select(0)
        
    def FillProfesseurs(self, debut=None, fin=None, site=None, inscrit=None):
        if creche.type != TYPE_GARDERIE_PERISCOLAIRE or not creche.professeurs:
            self.professeurs_choice.Show(False)
            return
        
        self.professeurs_choice.Show(True)
        self.professeurs_choice.Clear()
        self.professeurs_choice.Append("Tous les professeurs", None)
        for professeur in creche.professeurs:
            self.professeurs_choice.Append(professeur.prenom + " " + professeur.nom, professeur)
        self.professeurs_choice.Select(0)
    
    def FillInscrits(self, debut=None, fin=None, site=None, professeur=None):
        self.inscrits_choice.Clear()
        self.inscrits_choice.Append("Tous les inscrits", None)
        if debut is None and fin is None and site is None and professeur is None:
            inscrits = creche.inscrits
        else:
            inscrits = set()
            for inscrit in creche.inscrits:
                for inscription in inscrit.GetInscriptions(debut, fin):
                    if (site is None or inscription.site == site) and (professeur is None or inscription.professeur == professeur):
                        inscrits.add(inscrit)

        self.inscrits_choice.Clear()
        self.inscrits_choice.Append("Tous les inscrits", None)
        for inscrit in inscrits:
            self.inscrits_choice.Append(GetPrenomNom(inscrit), inscrit)
        self.inscrits_choice.Select(0)
        
    def UpdateContents(self):
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        if len(creche.sites) < 2:
            if self.site_col_displayed:
                self.grid.DeleteCols(1)
                self.site_col_displayed = 0
        else:
            if not self.site_col_displayed:
                self.grid.InsertCols(1)
                self.grid.SetColLabelValue(1, "Site")
                self.grid.SetColSize(1, 100)
                self.site_col_displayed = 1
        if creche.type == TYPE_GARDERIE_PERISCOLAIRE:
            if not self.professeur_col_displayed:
                self.grid.InsertCols(1+self.site_col_displayed)
                self.grid.SetColLabelValue(1+self.site_col_displayed, "Professeur")
                self.grid.SetColSize(1+self.site_col_displayed, 100)
                self.professeur_col_displayed = 1
        else:
            if self.professeur_col_displayed:
                self.grid.DeleteCols(1+self.site_col_displayed)
                self.professeur_col_displayed = 0
        self.grid.ForceRefresh()
        self.FillSites()
        self.FillProfesseurs()
        self.FillInscrits()
        self.sizer.FitInside(self)
    
    def onPeriodeChange(self, event):
        debut_value = self.debut_control.GetValue()
        fin_value = self.fin_control.GetValue()
        if debut_value != self.debut_value or fin_value != self.fin_value:
            self.debut_value = debut_value
            self.fin_value = fin_value
            kwargs = {"debut": debut_value, "fin": fin_value}
            for ctrl in self.ordered:
                selection = ctrl.GetStringSelection()
                ctrl.fill_function(**kwargs)
                ctrl.SetStringSelection(selection)
                if ctrl.GetSelection() == 0:
                    self.move_to_unordered(ctrl)
                else:
                    kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
            for ctrl in self.unordered:
                ctrl.fill_function(**kwargs)
        event.Skip()
    
    def move_to_unordered(self, object):
        kwargs = {"debut": self.debut_control.GetValue(), "fin": self.fin_control.GetValue()}
        index = self.ordered.index(object)
        self.ordered.remove(object)
        self.ordered_sizer.Detach(object)
        self.unordered.insert(0, object)
        self.unordered_sizer.Insert(0, object, 0, wx.LEFT, 5)
        for ctrl in self.ordered[:index]:
            kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
        for ctrl in self.ordered[index:]:
            selection = ctrl.GetStringSelection()
            ctrl.fill_function(**kwargs)
            ctrl.SetStringSelection(selection)
            kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
        for ctrl in self.unordered:
            ctrl.fill_function(**kwargs)
        self.sizer.Layout()
            
    def onChoice(self, event):
        object = event.GetEventObject()
        selection = object.GetSelection()
        value = object.GetClientData(selection)
        if value is None:
            if object in self.ordered:
                self.move_to_unordered(object)
        else:
            kwargs = {"debut": self.debut_control.GetValue(), "fin": self.fin_control.GetValue()}
            if object in self.unordered:
                self.unordered.remove(object)
                self.unordered_sizer.Detach(object)
                self.ordered.append(object)
                self.ordered_sizer.Add(object, 0, wx.LEFT, 5)
                self.sizer.Layout()
                for ctrl in self.ordered:
                    kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
                for ctrl in self.unordered:
                    ctrl.fill_function(**kwargs)
            else:
                index = self.ordered.index(object)
                for ctrl in self.ordered[:index]:
                    kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
                for ctrl in self.ordered[index:]:
                    selection = ctrl.GetStringSelection()
                    ctrl.fill_function(**kwargs)
                    ctrl.SetStringSelection(selection)
                    kwargs[ctrl.parameter] = ctrl.GetClientData(ctrl.GetSelection())
                for ctrl in self.unordered:
                    ctrl.fill_function(**kwargs)
        event.Skip()
        
    def GetSelection(self):
        debut = self.debut_control.GetValue()
        fin = self.fin_control.GetValue()
        if len(creche.sites) < 2:
            site = None
        else:
            site = self.sites_choice.GetClientData(self.sites_choice.GetSelection())
        if creche.type != TYPE_GARDERIE_PERISCOLAIRE or not creche.professeurs:
            professeur = None
        else:
            professeur = self.professeurs_choice.GetClientData(self.professeurs_choice.GetSelection())
        inscrit = self.inscrits_choice.GetClientData(self.inscrits_choice.GetSelection())
        if inscrit:
            inscrits = [inscrit]
        else:
            inscrits = creche.inscrits
        if not debut:
            debut = datetime.date(2004, 1, 1)
        if not fin:
            fin = last_date
        
        selection = {}
        for inscrit in inscrits:
            for inscription in inscrit.GetInscriptions(debut, fin):
                if (site is None or inscription.site == site) and (professeur is None or inscription.professeur == professeur):
                    date = max(debut, inscription.debut)
                    if inscription.fin:
                        date_fin = min(fin, inscription.fin)
                    else:
                        date_fin = fin
                    while date <= date_fin:
                        state = inscrit.GetState(date)
                        if state.state > 0 and state.state & PRESENT:
                            if date not in selection:
                                selection[date] = []
                            if date in inscrit.journees:
                                journee = inscrit.journees[date]
                            else:
                                journee = inscrit.GetJourneeReference(date)
                            arrivee, depart = journee.GetPlageHoraire()
                            # print date, arrivee, depart, journee.activites
                            selection[date].append((inscription.site, inscription.professeur, inscrit, arrivee, depart, state.heures_realisees, journee.commentaire))
                        date += datetime.timedelta(1)
        return selection
    
    def onOk(self, event):
        selection = self.GetSelection()
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        row = 0
        dates = selection.keys()
        dates.sort()
        for date in dates:
            for site, professeur, inscrit, heure_arrivee, heure_depart, heures, commentaire in selection[date]:
                self.grid.AppendRows(1)
                self.grid.SetCellValue(row, 0, date2str(date))
                inscrit_column = 1
                if self.site_col_displayed:
                    inscrit_column += 1
                    if site:
                        self.grid.SetCellValue(row, 1, site.nom)
                if self.professeur_col_displayed:
                    self.grid.SetCellValue(row, inscrit_column, GetPrenomNom(professeur))
                    inscrit_column += 1
                self.grid.SetCellValue(row, inscrit_column, GetPrenomNom(inscrit))
                self.grid.SetCellValue(row, inscrit_column+1, GetHeureString(heures))
                row += 1
        self.grid.ForceRefresh()
        
    def onExport(self, event):
        debut = self.debut_control.GetValue()
        fin = self.fin_control.GetValue()
        if len(creche.sites) < 2:
            site = None
        else:
            site = self.sites_choice.GetClientData(self.sites_choice.GetSelection())
        if creche.type != TYPE_GARDERIE_PERISCOLAIRE or not creche.professeurs:
            professeur = None
        else:
            professeur = self.professeurs_choice.GetClientData(self.professeurs_choice.GetSelection())
        inscrit = self.inscrits_choice.GetClientData(self.inscrits_choice.GetSelection())
        
        selection = self.GetSelection()
        DocumentDialog(self, EtatsPresenceModifications(debut, fin, site, professeur, inscrit, selection)).ShowModal()
          
class StatistiquesFrequentationTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sitechoice = wx.Choice(self)
        self.anneechoice = wx.Choice(self)
        for annee in range(first_date.year, last_date.year+1):
            self.anneechoice.Append(str(annee), annee)
        self.anneechoice.SetStringSelection(str(today.year))
        self.periodechoice = wx.Choice(self)
        for index, month in enumerate(months):
            self.periodechoice.Append(month, [index])
        self.periodechoice.Append("----") # TODO changer ça 
        for index, trimestre in enumerate(trimestres):
            self.periodechoice.Append(u"%s trimestre" % trimestre, [3*index, 3*index+1, 3*index+2])
        self.periodechoice.SetStringSelection(months[today.month-1])
        self.periodechoice.Append("----") # TODO changer ça 
        self.periodechoice.Append(u"Année complète", range(0, 12))
        for choice in (self.sitechoice, self.anneechoice, self.periodechoice):
            self.Bind(wx.EVT_CHOICE, self.OnChangementPeriode, choice)
        sizer.AddMany([(self.sitechoice, 0, 0, 0), (self.anneechoice, 0, wx.LEFT, 5), (self.periodechoice, 0, wx.LEFT, 5)])
        self.sizer.Add(sizer, 0, wx.EXPAND|wx.ALL, 10)
        
        self.message = wx.lib.expando.ExpandoTextCtrl(self)
        self.message.Disable()
        self.message.SetValue("")
        self.message.Show(False)
        self.sizer.Add(self.message, 0, wx.EXPAND|wx.ALL, 10)
        
        self.result_sizer = wx.FlexGridSizer(0, 3, 5, 10)
        self.presences_contrat_heures = wx.TextCtrl(self)
        self.presences_contrat_heures.Disable()
        self.presences_contrat_euros = wx.TextCtrl(self)
        self.presences_contrat_euros.Disable()
        self.result_sizer.AddMany([(wx.StaticText(self, -1, u'Présences contractualisées :'), 0, 0), (self.presences_contrat_heures, 0, wx.EXPAND), (self.presences_contrat_euros, 0, wx.EXPAND)])
        self.presences_realisees_heures = wx.TextCtrl(self)
        self.presences_realisees_heures.Disable()
        self.presences_realisees_euros = wx.TextCtrl(self)
        self.presences_realisees_euros.Disable()
        self.result_sizer.AddMany([(wx.StaticText(self, -1, u'Présences réalisées :'), 0, 0), (self.presences_realisees_heures, 0, wx.EXPAND), (self.presences_realisees_euros, 0, wx.EXPAND)])
        self.presences_facturees_heures = wx.TextCtrl(self)
        self.presences_facturees_heures.Disable()
        self.presences_facturees_euros = wx.TextCtrl(self)
        self.presences_facturees_euros.Disable()
        self.result_sizer.AddMany([(wx.StaticText(self, -1, u'Présences facturées :'), 0, 0), (self.presences_facturees_heures, 0, wx.EXPAND), (self.presences_facturees_euros, 0, wx.EXPAND)])       
        self.coefficient_remplissage = wx.TextCtrl(self)
        self.coefficient_remplissage.Disable()
        self.result_sizer.AddMany([(wx.StaticText(self, -1, u'Coefficient de remplissage :'), 0, 0), (self.coefficient_remplissage, 0, wx.EXPAND)])       
        self.sizer.Add(self.result_sizer, 0, wx.EXPAND|wx.ALL, 10)
        self.SetSizer(self.sizer)
        self.UpdateContents()
        self.Layout()
        
    def UpdateContents(self):
        if len(creche.sites) > 1:
            self.sitechoice.Show(True)
            site_selected = self.sitechoice.GetSelection()
            self.sitechoice.Clear()
            for site in creche.sites:
                self.sitechoice.Append(site.nom, site)
            if site_selected < 0 or site_selected >= self.sitechoice.GetCount():
                site_selected = 0
            self.sitechoice.SetSelection(site_selected)                
        else:
            self.sitechoice.Show(False)
        self.OnChangementPeriode(None)
        
    def OnChangementPeriode(self, evt):
        if len(creche.sites) > 1:
            current_site = self.sitechoice.GetSelection()
            site = self.sitechoice.GetClientData(current_site)
        else:
            site = None

        annee = self.anneechoice.GetClientData(self.anneechoice.GetSelection())
        periode = self.periodechoice.GetClientData(self.periodechoice.GetSelection())
        if periode is None:
            return
        
        heures_contrat = 0.0
        heures_facture = 0.0
        heures_contractualisees = 0.0
        heures_realisees = 0.0
        heures_facturees = 0.0
        cotisations_contractualisees = 0.0
        cotisations_realisees = 0.0
        cotisations_facturees = 0.0
        heures_accueil = 0.0
        total = 0.0
        erreurs = []
        for mois in periode:
            debut = datetime.date(annee, mois+1, 1)
            fin = GetMonthEnd(debut)
            heures_accueil += GetHeuresAccueil(annee, mois+1, site)
            print "Statistiques %s %d" % (months[mois], annee)
            for inscrit in creche.inscrits:
                try:
                    inscriptions = inscrit.GetInscriptions(debut, fin)
                    if inscriptions and (site is None or inscriptions[0].site == site):
                        facture = Facture(inscrit, annee, mois+1)
                        heures_contrat += facture.heures_contrat
                        heures_facture += facture.heures_facture
                        heures_contractualisees += facture.heures_contractualisees
                        heures_realisees += facture.heures_realisees
                        heures_facturees += facture.heures_facturees
                        cotisations_contractualisees += facture.total_contractualise
                        cotisations_realisees += facture.total_realise
                        cotisations_facturees += facture.total_facture
                        total += facture.total
                        print inscrit.prenom, inscrit.nom, facture.date
                        print ' ', u"heures contractualisées :", facture.heures_contractualisees, facture.heures_contrat
                        print ' ', u"heures réalisées :", facture.heures_realisees
                        print ' ', u"heures facturées :", facture.heures_facturees, facture.heures_facture
                        print ' ', u"total contractualisé", facture.total_contractualise
                        print ' ', u"total réalisé :", facture.total_realise
                        print ' ', u"total facturé :", facture.total_facture
                        
                except Exception, e:
                    erreurs.append((inscrit, e))
                              
        if erreurs:
            msg = u"\n\n".join([u"%s %s:\n%s" % (inscrit.prenom, inscrit.nom, unicode(erreur)) for inscrit, erreur in erreurs])
            self.message.SetValue(msg)
            self.message.Show(True)
            self.presences_contrat_heures.SetValue("-")
            self.presences_realisees_heures.SetValue("-")
            self.presences_facturees_heures.SetValue("-")
            self.presences_contrat_euros.SetValue("-")
            self.presences_realisees_euros.SetValue("-")
            self.presences_facturees_euros.SetValue("-")
            self.coefficient_remplissage.SetValue("-")
        else:
            self.message.Show(False)
            if creche.nom == "Dessine moi un mouton" or (config.options & HEURES_CONTRAT):
                presences_contrat_heures = heures_contrat
                presences_facturees_heures = heures_facture
            else:
                presences_contrat_heures = heures_contractualisees
                presences_facturees_heures = heures_facturees
                                
            self.presences_contrat_heures.SetValue("%.2f heures" % presences_contrat_heures)
            self.presences_realisees_heures.SetValue("%.2f heures" % heures_realisees)
            self.presences_facturees_heures.SetValue("%.2f heures" % presences_facturees_heures)
            self.presences_contrat_euros.SetValue(u"%.2f €" % cotisations_contractualisees)
            self.presences_realisees_euros.SetValue(u"%.2f €" % cotisations_realisees)
            self.presences_facturees_euros.SetValue(u"%.2f €" % cotisations_facturees)
            coeff_remplissage = 0.0
            if heures_accueil:
                coeff_remplissage = (100.0 * heures_facturees) / heures_accueil
            self.coefficient_remplissage.SetValue(u"%.1f %%" % coeff_remplissage)

        self.sizer.FitInside(self)
        self.Layout()

class RelevesTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        today = datetime.date.today()
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.site_choice = wx.Choice(self, -1)
        self.sizer.Add(self.site_choice, 0, wx.TOP|wx.BOTTOM, 5)
        
        # Les coordonnees des parents
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Coordonnées des parents'), wx.HORIZONTAL)
        self.coords_date = wx.TextCtrl(self)
        self.coords_date.SetValue("Aujourd'hui")
        button = wx.Button(self, -1, u'Génération')
        self.Bind(wx.EVT_BUTTON, self.OnGenerationCoordonnees, button)
        box_sizer.AddMany([(self.coords_date, 1, wx.EXPAND|wx.ALL, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        # Les contrats en cours
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Inscriptions en cours'), wx.HORIZONTAL)
        self.inscriptions_date = wx.TextCtrl(self)
        self.inscriptions_date.SetValue("Aujourd'hui")
        button = wx.Button(self, -1, u'Génération')
        self.Bind(wx.EVT_BUTTON, self.OnGenerationEtatsInscriptions, button)
        box_sizer.AddMany([(self.inscriptions_date, 1, wx.EXPAND|wx.ALL, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)

        # Les releves trimestriels
        if IsTemplateFile("Releve SIEJ.odt"):
            box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Relevés trimestriels (SIEJ)'), wx.HORIZONTAL)
            self.releves_choice = wx.Choice(self)
            button = wx.Button(self, -1, u'Génération')
            for year in range(first_date.year, today.year + 1):
                self.releves_choice.Append(u"Année %d" % year, year)
            #    for index, trimestre in enumerate(trimestres):
            #        self.releves_choice.Append(u"%s trimestre %d" % (trimestre, year), datetime.date(year, 1+3*index, 1))
            self.releves_choice.SetSelection(today.year-first_date.year)
            self.Bind(wx.EVT_BUTTON, self.OnGenerationReleveSIEJ, button)
            box_sizer.AddMany([(self.releves_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
            self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        else:
            box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Relevés trimestriels'), wx.HORIZONTAL)
            self.releves_choice = wx.Choice(self)
            button = wx.Button(self, -1, u'Génération')
            for year in range(first_date.year, today.year + 1):
                self.releves_choice.Append(u'Année %d' % year, year)
            self.releves_choice.SetSelection(today.year - first_date.year)
            self.Bind(wx.EVT_BUTTON, self.OnGenerationEtatsTrimestriels, button)
            box_sizer.AddMany([(self.releves_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
            self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
                
        # Les relevés détaillés
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Relevés annuels détaillés'), wx.HORIZONTAL)
        self.releves_detailles_choice = wx.Choice(self)
        button = wx.Button(self, -1, u'Génération')
        for year in range(first_date.year, today.year + 1):
            self.releves_detailles_choice.Append(u'Année %d' % year, year)
        self.releves_detailles_choice.SetSelection(today.year - first_date.year)
        self.Bind(wx.EVT_BUTTON, self.OnGenerationRelevesDetailles, button)
        box_sizer.AddMany([(self.releves_detailles_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        # Les etats des places
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Etats des places'), wx.HORIZONTAL)
        self.places_choice = wx.Choice(self)
        button = wx.Button(self, -1, u'Génération')
        for year in range(first_date.year, today.year + 1):
            self.places_choice.Append(u'Année %d' % year, year)
        self.places_choice.SetSelection(today.year - first_date.year)
        self.Bind(wx.EVT_BUTTON, self.OnGenerationEtatsPlaces, button)
        box_sizer.AddMany([(self.places_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        # Les rapports de fréquentation
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Rapports de fréquentation'), wx.HORIZONTAL)
        self.rapports_choice = wx.Choice(self)
        button = wx.Button(self, -1, u'Génération')
        for year in range(first_date.year, today.year + 1):
            self.rapports_choice.Append(u'Année %d' % year, year)
        self.rapports_choice.SetSelection(today.year - first_date.year)
        self.Bind(wx.EVT_BUTTON, self.OnGenerationRapportFrequentation, button)
        box_sizer.AddMany([(self.rapports_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        if IsTemplateFile("Etat presence mensuel.ods"):
            box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Etat de présence mensuel'), wx.HORIZONTAL)
            self.etat_presence_mensuesl_choice = wx.Choice(self)
            button = wx.Button(self, -1, u'Génération')
            date = first_date
            while date < last_date:
                self.etat_presence_mensuesl_choice.Append(u'%s %d' % (months[date.month-1], date.year), date)
                date = GetNextMonthStart(date)
            self.etat_presence_mensuesl_choice.SetSelection((today.year - first_date.year)*12 + today.month - first_date.month)
            self.Bind(wx.EVT_BUTTON, self.OnGenerationEtatPresenceMensuel, button)
            box_sizer.AddMany([(self.etat_presence_mensuesl_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
            self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        # Les synthèses financières
        if IsTemplateFile("Synthese financiere.ods"):
            box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Synthèse financière'), wx.HORIZONTAL)
            self.syntheses_choice = wx.Choice(self)
            button = wx.Button(self, -1, u'Génération')
            for year in range(first_date.year, today.year + 1):
                self.syntheses_choice.Append(u'Année %d' % year, year)
            self.syntheses_choice.SetSelection(today.year - first_date.year)
            self.Bind(wx.EVT_BUTTON, self.OnGenerationSyntheseFinanciere, button)
            box_sizer.AddMany([(self.syntheses_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
            self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)

        # Les commandes de repas
        if IsTemplateFile("Commande repas.odt"):
            box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Commande de repas'), wx.HORIZONTAL)
            self.commande_repas_choice = wx.Choice(self)
            PopulateWeekChoice(self.commande_repas_choice)
            button = wx.Button(self, -1, u'Génération')
            self.Bind(wx.EVT_BUTTON, self.OnGenerationCommandeRepas, button)
            box_sizer.AddMany([(self.commande_repas_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
            self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)
        
        # Les plannings de presence enfants
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Planning des présences'), wx.HORIZONTAL)
        self.planning_hebdo_choice = wx.Choice(self)
        PopulateWeekChoice(self.planning_hebdo_choice)
        button = wx.Button(self, -1, u'Génération')
        self.Bind(wx.EVT_BUTTON, self.OnGenerationPlanningPresences, button)
        box_sizer.AddMany([(self.planning_hebdo_choice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)

        # Les plannings détaillés
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Planning détaillé'), wx.HORIZONTAL)
        self.detail_start_date = DateCtrl(self)
        self.detail_end_date = DateCtrl(self)
        day = today
        while day in creche.jours_fermeture:
            day += datetime.timedelta(1)
        self.detail_start_date.SetValue(day)
        button = wx.Button(self, -1, u'Génération')
        self.Bind(wx.EVT_BUTTON, self.OnGenerationPlanningDetaille, button)
        box_sizer.AddMany([(self.detail_start_date, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5), (wx.StaticText(self, -1, "-"), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5), (self.detail_end_date, 1, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5), (button, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)])
        self.sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)

        self.UpdateContents()        
        self.SetSizer(self.sizer)

    def UpdateContents(self):
        if len(creche.sites) > 1:
            self.site_choice.Show(True)
            site_selected = self.site_choice.GetSelection()
            self.site_choice.Clear()
            for site in creche.sites:
                self.site_choice.Append(site.nom, site)
            if site_selected < 0 or site_selected >= self.site_choice.GetCount():
                site_selected = 0
            self.site_choice.SetSelection(site_selected)                
        else:
            self.site_choice.Show(False)
    
    def GetSelectedSite(self):
        if len(creche.sites) > 1:
            current_site = self.site_choice.GetSelection()
            return self.site_choice.GetClientData(current_site)
        else:
            return None
            
    def OnGenerationCoordonnees(self, evt):
        site = self.GetSelectedSite()
        date = str2date(self.coords_date.GetValue())
        DocumentDialog(self, CoordonneesModifications(site, date)).ShowModal()

    def OnGenerationEtatsInscriptions(self, evt):
        site = self.GetSelectedSite()
        date = str2date(self.inscriptions_date.GetValue())
        DocumentDialog(self, EtatsInscriptionsModifications(site, date)).ShowModal()

    def OnGenerationReleveSIEJ(self, evt):
        site = self.GetSelectedSite()
        annee = self.releves_choice.GetClientData(self.releves_choice.GetSelection())
        DocumentDialog(self, ReleveSIEJModifications(site, annee)).ShowModal()
        
    def OnGenerationEtatsTrimestriels(self, evt):
        site = self.GetSelectedSite()
        annee = self.releves_choice.GetClientData(self.releves_choice.GetSelection())
        DocumentDialog(self, EtatsTrimestrielsModifications(site, annee)).ShowModal()
    
    def OnGenerationRelevesDetailles(self, evt):
        site = self.GetSelectedSite()
        annee = self.releves_detailles_choice.GetClientData(self.releves_detailles_choice.GetSelection())
        DocumentDialog(self, ReleveDetailleModifications(site, annee)).ShowModal()
        
    def OnGenerationEtatsPlaces(self, evt):
        site = self.GetSelectedSite()
        annee = self.places_choice.GetClientData(self.places_choice.GetSelection())
        DocumentDialog(self, EtatPlacesModifications(site, annee)).ShowModal()
        
    def OnGenerationRapportFrequentation(self, evt):
        site = self.GetSelectedSite()
        annee = self.rapports_choice.GetClientData(self.rapports_choice.GetSelection())
        DocumentDialog(self, RapportFrequentationModifications(site, annee)).ShowModal()
        
    def OnGenerationEtatPresenceMensuel(self, evt):
        site = self.GetSelectedSite()
        date = self.etat_presence_mensuesl_choice.GetClientData(self.etat_presence_mensuesl_choice.GetSelection())
        DocumentDialog(self, EtatPresenceMensuelModifications(site, date)).ShowModal()
        
    def OnGenerationSyntheseFinanciere(self, evt):
        annee = self.syntheses_choice.GetClientData(self.syntheses_choice.GetSelection())
        DocumentDialog(self, SyntheseFinanciereModifications(annee)).ShowModal()

    def OnGenerationCommandeRepas(self, evt):
        semaine = self.commande_repas_choice.GetClientData(self.commande_repas_choice.GetSelection())
        DocumentDialog(self, CommandeRepasModifications(semaine)).ShowModal()

    def OnGenerationPlanningPresences(self, evt):
        site = self.GetSelectedSite()
        date = self.planning_hebdo_choice.GetClientData(self.planning_hebdo_choice.GetSelection())
        DocumentDialog(self, PlanningModifications(site, date)).ShowModal()
            
    def OnGenerationPlanningDetaille(self, evt):
        site = self.GetSelectedSite()
        start = self.detail_start_date.GetValue()
        end = self.detail_end_date.GetValue()
        if end is None:
            end = start
        DocumentDialog(self, PlanningDetailleModifications((start, end), site)).ShowModal()
        
class AlertesTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.grid.Grid(self)
        self.grid.CreateGrid(0, 3)
        self.grid.SetRowLabelSize(1)
        self.grid.SetColLabelValue(0, "ID")
        self.grid.SetColLabelValue(1, "Date")
        self.grid.SetColLabelValue(2, u"Libellé")
        self.grid.SetColSize(0, 30)
        self.grid.SetColSize(1, 100)
        self.grid.SetColSize(2, 500)
        self.UpdateContents()
        self.sizer.Add(self.grid, -1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(self.sizer)

    def UpdateContents(self):
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(0, self.grid.GetNumberRows())
        alertes = creche.alertes.values()
        alertes.sort(key=lambda alerte: alerte.date)
        for row, alerte in enumerate(alertes):    
            self.grid.AppendRows(1)
            self.grid.SetCellValue(row, 0, str(row+1))
            self.grid.SetCellValue(row, 1, date2str(alerte.date))
            self.grid.SetCellValue(row, 2, alerte.texte)

        self.grid.ForceRefresh()

class SalariesTab(AutoTab):
    def __init__(self, parent):
        AutoTab.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.salaries_choice = {}
        
        # Les Etats mensuels des salariés
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u'Relevés mensuels'), wx.HORIZONTAL)
        self.salaries_choice["releves"] = wx.Choice(self)
        self.releves_monthchoice = wx.Choice(self)
        self.Bind(wx.EVT_CHOICE, self.EvtRelevesSalarieChoice, self.salaries_choice["releves"])
        self.Bind(wx.EVT_CHOICE, self.EvtRelevesMonthChoice, self.releves_monthchoice)
        button = wx.Button(self, -1, u'Génération')
        self.Bind(wx.EVT_BUTTON, self.OnGenerationReleve, button)
        box_sizer.AddMany([(self.salaries_choice["releves"], 1, wx.ALL|wx.EXPAND, 5), (self.releves_monthchoice, 1, wx.ALL|wx.EXPAND, 5), (button, 0, wx.ALL, 5)])
        sizer.Add(box_sizer, 0, wx.EXPAND|wx.BOTTOM, 10)

        self.SetSizer(sizer)
        self.UpdateContents()
        self.Layout()

    def EvtRelevesSalarieChoice(self, evt):
        selection = self.releves_monthchoice.GetStringSelection()
        self.releves_monthchoice.Clear()
        salarie = self.salaries_choice["releves"].GetClientData(self.salaries_choice["releves"].GetSelection())
        date = GetFirstMonday()
        while date <= datetime.date.today():
            if isinstance(salarie, list) or salarie.GetContrat(date):
                self.releves_monthchoice.Append('%s %d' % (months[date.month - 1], date.year), date)
            date = GetNextMonthStart(date)
        self.releves_monthchoice.SetSelection(self.releves_monthchoice.GetCount()-1)
        self.EvtRelevesMonthChoice()
        
    def EvtRelevesMonthChoice(self, evt=None):
        pass
    
    def UpdateContents(self):
        for choice in self.salaries_choice.values():
            choice.Clear()
            choice.Append(u'Tous les salariés', creche.salaries)
            
        salaries = { }
        autres = { }
        for salarie in creche.salaries:
            if salarie.GetContrat(datetime.date.today()) != None:
                salaries[GetPrenomNom(salarie)] = salarie
            else:
                autres[GetPrenomNom(salarie)] = salarie
        
        keys = salaries.keys()
        keys.sort()
        for key in keys:
            for choice in self.salaries_choice.values():
                choice.Append(key, salaries[key])
        
        if len(salaries) > 0 and len(autres) > 0:
            for choice in self.salaries_choice.values():
                choice.Append(20 * '-', None)
        
        keys = autres.keys()
        keys.sort()
        for key in keys:
            for choice in self.salaries_choice.values():
                choice.Append(key, autres[key])
            
        for choice in self.salaries_choice.values():
            choice.SetSelection(0)
        
        self.EvtRelevesSalarieChoice(None)
        
        self.Layout()
        
    def __get_releves_salaries_periode(self):
        salaries = self.salaries_choice["releves"].GetClientData(self.salaries_choice["releves"].GetSelection())
        periode = self.releves_monthchoice.GetClientData(self.releves_monthchoice.GetSelection())
        if isinstance(salaries, list):
            salaries = [salarie for salarie in salaries if salarie.GetContrat(periode)]
        else:
            salaries = [salaries]
        return salaries, periode

    def OnGenerationReleve(self, evt):
        salaries, periode = self.__get_releves_salaries_periode()
        DocumentDialog(self, ReleveSalariesModifications(salaries, periode)).ShowModal()
        
                
class TableauxDeBordNotebook(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, style=wx.LB_DEFAULT)
        self.AddPage(PlacesDisponiblesTab(self), "Places disponibles")
        self.AddPage(EtatsPresenceTab(self), u"Etats de présence")
        self.AddPage(StatistiquesFrequentationTab(self), u'Statistiques de fréquentation')
        self.AddPage(RelevesTab(self), u'Edition de relevés')
        self.AddPage(SalariesTab(self), u'Salariés')
        if creche.gestion_alertes:
            self.AddPage(AlertesTab(self), u'Alertes')

    def UpdateContents(self):
        for page in range(self.GetPageCount()):
            self.GetPage(page).UpdateContents()
        
class TableauxDeBordPanel(GPanel):
    name = "Tableaux de bord"
    bitmap = GetBitmapFile("tableaux-bord.png")
    profil = PROFIL_ALL
    def __init__(self, parent):
        GPanel.__init__(self, parent, u'Tableaux de bord')
        self.notebook = TableauxDeBordNotebook(self)
        self.sizer.Add(self.notebook, 1, wx.EXPAND)

    def UpdateContents(self):
        self.notebook.UpdateContents()