//
// ********************************************************************
// * 许可证与免责声明                                           *
// *                                                                  *
// * Geant4 软件版权归以下版权持有者所有： *
// * Geant4 协作组。软件按以下条款提供： *
// * Geant4 软件许可证条款，包含在文件中： *
// * LICENSE，或访问 http://cern.ch/geant4/license 。其中 *
// * 包含版权持有者列表。                             *
// *                                                                  *
// * 本软件系统作者及其所属机构， *
// * 以及提供经费支持的机构， *
// * 均不对本软件作任何明示或暗示担保， *
// * 也不对本软件系统承担任何责任。 *
// * 有关使用条款请参见 LICENSE 文件及上述网址， *
// * 以获取完整免责声明与责任限制。         *
// *                                                                  *
// * 本代码实现源自 GEANT4 协作组的科学与 *
// * 技术工作成果。                      *
// * 使用、复制、修改或分发本软件（或 *
// * 基于本软件的任何成果）即表示你同意在 *
// * 相关科学出版物中致谢其使用，并表示你 *
// * 接受 Geant4 软件许可证的全部条款。          *
// ********************************************************************
//
// 
/// \file DetectorMessenger.cc
/// \brief DetectorMessenger 类的实现

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
  fDetDirectory->SetGuidance("探测器 construction control");


  fTargetShiftDistance = new G4UIcmdWithADoubleAndUnit("/Xray/det/SetObjShift",this);
  fTargetShiftDistance->SetGuidance("Select Shift Distance of the Object.");
  fTargetShiftDistance->SetParameterName("Size",false);
  fTargetShiftDistance->SetRange("Size>-99999.");
  fTargetShiftDistance->SetUnitCategory("Length");
  fTargetShiftDistance->AvailableForStates(G4State_PreInit,G4State_Idle);
  // 影响几何的命令：在多线程模式下广播到工作线程。
  fTargetShiftDistance->SetToBeBroadcasted(true);

  fLoadGDMLCmd = new G4UIcmdWithAString("/Xray/det/loadGDML",this);
  fLoadGDMLCmd->SetGuidance("Load ore geometry from GDML file.");
  fLoadGDMLCmd->SetParameterName("filename",false);
  fLoadGDMLCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  // 多线程关键：确保工作线程收到 GDML 替换命令。
  fLoadGDMLCmd->SetToBeBroadcasted(true);

  fMaterialSlabMaterialCmd = new G4UIcmdWithAString("/Xray/det/SetMaterialSlabMaterial",this);
  fMaterialSlabMaterialCmd->SetGuidance("Set material for the material slab (H2O, CHO, C, Al, Fe, Cu, Pb).");
  fMaterialSlabMaterialCmd->SetParameterName("material",false);
  fMaterialSlabMaterialCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  // 保持所有线程中的几何/材质状态一致。
  fMaterialSlabMaterialCmd->SetToBeBroadcasted(true);

  fMaterialSlabThicknessCmd = new G4UIcmdWithADoubleAndUnit("/Xray/det/SetMaterialSlabThickness",this);
  fMaterialSlabThicknessCmd->SetGuidance("Set thickness of the material slab.");
  fMaterialSlabThicknessCmd->SetParameterName("thickness",false);
  fMaterialSlabThicknessCmd->SetRange("thickness>=0.");
  fMaterialSlabThicknessCmd->SetUnitCategory("Length");
  fMaterialSlabThicknessCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  // 保持所有线程中的几何/材质状态一致。
  fMaterialSlabThicknessCmd->SetToBeBroadcasted(true);

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
