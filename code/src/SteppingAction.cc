#include "SteppingAction.hh"
#include "EventAction.hh"
#include "G4SteppingManager.hh"
#include "DetectorConstruction.hh"
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4NistManager.hh"
#include "G4Material.hh"
#include <mutex>

using namespace std;	 

SteppingAction::SteppingAction(EventAction* EvAct)
:eventAction(EvAct)
{
    // 缓存探测器像素数量（避免每次步进都查询）
    const auto detConstruction = static_cast<const DetectorConstruction*>(
        G4RunManager::GetRunManager()->GetUserDetectorConstruction());
    fDetNum = detConstruction->DetPixNum;
    
    // 初始化材料指针为nullptr，将在第一次使用时延迟初始化
    fGOSMaterial = nullptr;
    fGGAGMaterial = nullptr;
}

SteppingAction::~SteppingAction()
{ }

void SteppingAction::UserSteppingAction(const G4Step* aStep)
{
	// 优化：先检查能量沉积，避免不必要的材料查找
	G4double EdepStep = aStep->GetTotalEnergyDeposit();
	if (EdepStep <= 0.0) {
		return;  // 提前返回，避免后续计算
	}
	
	auto fpPreStepPoint = aStep->GetPreStepPoint();
	const G4Material* material = fpPreStepPoint->GetMaterial();
	
	// 延迟初始化材料指针（在几何构建完成后，使用静态变量确保只查找一次）
	// 使用线程安全的初始化方式，静态变量在所有线程间共享
	static std::once_flag initFlag;
	static const G4Material* staticGOSMaterial = nullptr;
	static const G4Material* staticGGAGMaterial = nullptr;
	
	std::call_once(initFlag, []() {
		// 通过名称查找材料（只执行一次，所有线程共享）
		G4MaterialTable* matTable = G4Material::GetMaterialTable();
		for (auto* mat : *matTable) {
			const G4String& name = mat->GetName();
			if (name == "GOS") {
				staticGOSMaterial = mat;
			} else if (name == "GGAG") {
				staticGGAGMaterial = mat;
			}
		}
	});
	
	// 将静态材料指针赋值给成员变量（每个线程实例都有自己的成员变量）
	if (!fGOSMaterial || !fGGAGMaterial) {
		fGOSMaterial = staticGOSMaterial;
		fGGAGMaterial = staticGGAGMaterial;
	}
	
	// 快速路径：如果材料不匹配，直接返回（避免后续计算）
	if (material != fGOSMaterial && material != fGGAGMaterial) {
		return;
	}
	
	// 转换为keV单位（只对感兴趣的材料执行）
	EdepStep /= keV;
	
	// 获取CopyNumber并计算像素索引
	G4int CopyNum = fpPreStepPoint->GetTouchable()->GetCopyNumber();
	G4int CoNo = CopyNum % fDetNum;
	
	// 使用指针比较代替字符串比较（更快）
	if (material == fGOSMaterial) {
		eventAction->EdepInCrystal2[CoNo] += EdepStep;
	} else {  // 必须是GGAG
		eventAction->EdepInCrystal[CoNo] += EdepStep;
	}
}
