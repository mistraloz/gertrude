# -*- coding: utf-8 -*-

import sys, os, __builtin__
sys.path.append("..")
import unittest
import sqlinterface
from sqlobjects import *
from cotisation import *

class GertrudeTests(unittest.TestCase):
    def test_creation_bdd(self):
        filename = "gertrude.db"
        if os.path.isfile(filename):
            os.remove(filename)
        con = sqlinterface.SQLConnection(filename)
        con.Create()

class PAJETests(unittest.TestCase):
    def test_paje(self):
        __builtin__.creche = Creche()
        creche.mode_facturation = FACTURATION_PAJE
        bureau = Bureau(creation=False)
        bureau.debut = datetime.date(2010, 1, 1)
        creche.bureaux.append(bureau)
        inscrit = Inscrit(creation=False)
        inscrit.prenom, inscrit.nom = 'gertrude', 'gertrude'
        inscrit.papa = Parent(inscrit, creation=False)
        inscrit.maman = Parent(inscrit, creation=False)
        inscription = Inscription(inscrit, creation=False)
        inscription.debut = datetime.date(2010, 1, 1)
        inscrit.inscriptions.append(inscription)
        self.assertRaises(CotisationException, Cotisation, inscrit, (datetime.date(2010, 1, 1), None), NO_ADDRESS|NO_PARENTS)
        creche.formule_taux_horaire = [["", 0.0]]
        creche.update_formule_taux_horaire(changed=False)
        cotisation = Cotisation(inscrit, (datetime.date(2010, 1, 1), None), NO_ADDRESS|NO_PARENTS)

class MarmousetsTests(unittest.TestCase):
    def test_1(self):
        __builtin__.creche = Creche()
        creche.mode_facturation = FACTURATION_PSU
        creche.temps_facturation = FACTURATION_DEBUT_MOIS
        creche.conges_inscription = 1
        for label in ("Week-end", "1er janvier", "1er mai", "8 mai", "14 juillet", u"15 août", "1er novembre", "11 novembre", u"25 décembre", u"Lundi de Pâques", "Jeudi de l'Ascension"):
            conge = Conge(creche, creation=False)
            conge.debut = label
            creche.add_conge(conge)
        conge = Conge(creche, creation=False)
        conge.debut = conge.fin = "14/05/2010"
        creche.add_conge(conge)
        bareme = BaremeCAF(creation=False)
        bareme.debut, bareme.plancher, bareme.plafond = datetime.date(2010, 1, 1), 6876.00, 53400.00
        creche.baremes_caf.append(bareme)
        bureau = Bureau(creation=False)
        bureau.debut = datetime.date(2010, 1, 1)
        creche.bureaux.append(bureau)
        inscrit = Inscrit(creation=False)
        inscrit.prenom, inscrit.nom = 'gertrude', 'gertrude'
        inscrit.papa = Parent(inscrit, creation=False)
        revenu = Revenu(inscrit.papa, creation=False)
        revenu.debut, revenu.revenu = datetime.date(2008, 1, 1), 30000.0
        inscrit.papa.revenus.append(revenu)
        inscrit.maman = Parent(inscrit, creation=False)
        revenu = Revenu(inscrit.maman, creation=False)
        revenu.debut, revenu.revenu = datetime.date(2008, 1, 1), 0.0
        inscrit.maman.revenus.append(revenu)
        inscription = Inscription(inscrit, creation=False)
        inscription.debut = datetime.date(2010, 1, 4)
        inscription.fin = datetime.date(2010, 7, 30)
        inscription.reference[1].add_activity(102, 210, 0, -1)
        inscription.reference[2].add_activity(102, 210, 0, -1)
        inscription.reference[3].add_activity(102, 210, 0, -1)
        inscription.reference[4].add_activity(102, 222, 0, -1)
        inscrit.inscriptions.append(inscription)
        conge = CongeInscrit(inscrit, creation=False)
        conge.debut, conge.fin = "01/02/2010", "20/02/2010"
        inscrit.add_conge(conge)
        cotisation = Cotisation(inscrit, (datetime.date(2010, 1, 4), None), NO_ADDRESS|NO_PARENTS)
        self.assertEquals(float("%.2f" % cotisation.heures_semaine), 37.0)
        self.assertEquals(cotisation.heures_annee, 971.0)
        self.assertEquals(cotisation.nombre_factures, 7)



if __name__ == '__main__':
    unittest.main()
