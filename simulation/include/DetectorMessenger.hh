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
/// \file DetectorMessenger.hh
/// \brief DetectorMessenger 类定义

#ifndef DetectorMessenger_h
#define DetectorMessenger_h 1

#include "globals.hh"
#include "G4UImessenger.hh"

class DetectorConstruction;
class G4UIdirectory;
class G4UIcmdWithAString;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWithABool;

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

/// Messenger class that defines commands for B2bDetectorConstruction.
///
/// It implements commands:
/// - /B2/det/setTargetMaterial name
/// - /B2/det/setChamberMaterial name
/// - /B2/det/stepMax value unit

class DetectorMessenger: public G4UImessenger
{
  public:
    DetectorMessenger(DetectorConstruction* );
    virtual ~DetectorMessenger();
    
    virtual void SetNewValue(G4UIcommand*, G4String);
    
  private:
    DetectorConstruction*  fDetectorConstruction;

    G4UIdirectory*           fB2Directory;
    G4UIdirectory*           fDetDirectory;

    G4UIcmdWithADoubleAndUnit*      fTargetShiftDistance;
    G4UIcmdWithABool*               fEnableObjectCmd;
    G4UIcmdWithAString*             fLoadGDMLCmd;
    G4UIcmdWithAString*             fMaterialSlabMaterialCmd;
    G4UIcmdWithADoubleAndUnit*      fMaterialSlabThicknessCmd;
};

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#endif
