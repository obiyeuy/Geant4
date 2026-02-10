//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
// 
/// \file DetectorMessenger.cc
/// \brief Implementation of the DetectorMessenger class

#include "DetectorMessenger.hh"
#include "DetectorConstruction.hh"

#include "G4UIdirectory.hh"
#include "G4UIcmdWithAString.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

DetectorMessenger::DetectorMessenger(DetectorConstruction* Det)
 : G4UImessenger(),
   fDetectorConstruction(Det)
{
  fB2Directory = new G4UIdirectory("/Xray/");
  fB2Directory->SetGuidance("UI commands specific to this example.");

  fDetDirectory = new G4UIdirectory("/Xray/det/");
  fDetDirectory->SetGuidance("Detector construction control");


  fTargetShiftDistance = new G4UIcmdWithADoubleAndUnit("/Xray/det/SetObjShift",this);
  fTargetShiftDistance->SetGuidance("Select Shift Distance of the Object.");
  fTargetShiftDistance->SetParameterName("Size",false);
  fTargetShiftDistance->SetRange("Size>-99999.");
  fTargetShiftDistance->SetUnitCategory("Length");
  fTargetShiftDistance->AvailableForStates(G4State_PreInit,G4State_Idle);
  fTargetShiftDistance->SetToBeBroadcasted(false);

  fLoadGDMLCmd = new G4UIcmdWithAString("/Xray/det/loadGDML",this);
  fLoadGDMLCmd->SetGuidance("Load ore geometry from GDML file.");
  fLoadGDMLCmd->SetParameterName("filename",false);
  fLoadGDMLCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fLoadGDMLCmd->SetToBeBroadcasted(false);

  fMaterialSlabMaterialCmd = new G4UIcmdWithAString("/Xray/det/SetMaterialSlabMaterial",this);
  fMaterialSlabMaterialCmd->SetGuidance("Set material for the material slab (H2O, CHO, C, Al, Fe, Cu, Pb).");
  fMaterialSlabMaterialCmd->SetParameterName("material",false);
  fMaterialSlabMaterialCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fMaterialSlabMaterialCmd->SetToBeBroadcasted(false);

  fMaterialSlabThicknessCmd = new G4UIcmdWithADoubleAndUnit("/Xray/det/SetMaterialSlabThickness",this);
  fMaterialSlabThicknessCmd->SetGuidance("Set thickness of the material slab.");
  fMaterialSlabThicknessCmd->SetParameterName("thickness",false);
  fMaterialSlabThicknessCmd->SetRange("thickness>=0.");
  fMaterialSlabThicknessCmd->SetUnitCategory("Length");
  fMaterialSlabThicknessCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fMaterialSlabThicknessCmd->SetToBeBroadcasted(false);

}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

DetectorMessenger::~DetectorMessenger()
{
  
  delete fTargetShiftDistance;
  delete fLoadGDMLCmd;
  delete fMaterialSlabMaterialCmd;
  delete fMaterialSlabThicknessCmd;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void DetectorMessenger::SetNewValue(G4UIcommand* command,G4String newValue)
{
  if( command == fTargetShiftDistance )
   { fDetectorConstruction->SetObjShiftDistance(fTargetShiftDistance->GetNewDoubleValue(newValue));}
  else if( command == fLoadGDMLCmd )
   { fDetectorConstruction->LoadOreGDML(newValue);}
  else if( command == fMaterialSlabMaterialCmd )
   { fDetectorConstruction->SetMaterialSlabMaterial(newValue);}
  else if( command == fMaterialSlabThicknessCmd )
   { fDetectorConstruction->SetMaterialSlabThickness(fMaterialSlabThicknessCmd->GetNewDoubleValue(newValue));}

}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
