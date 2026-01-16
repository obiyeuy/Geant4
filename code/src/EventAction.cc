
#include "EventAction.hh"

//#include "Randomize.hh" // do we really need this?
#include <iomanip>
#include <cstring>  // for memset

#include "RunAction.hh"
// #include "Analysis.hh"
// 旧版输出依赖的头文件（保留作参考，已不再使用）
// #include "G4AnalysisManager.hh"
#include "G4ParticleGun.hh"
#include "PrimaryGeneratorAction.hh"
#include "G4RunManager.hh"

#include "G4Event.hh"
#include "G4EventManager.hh"
#include "G4UnitsTable.hh"
#include "globals.hh"
#include "DetectorConstruction.hh"
//#include "iomanip"

using namespace std;
using namespace CLHEP;




EventAction::EventAction(RunAction* RuAct)
:G4UserEventAction(),runAction(RuAct)
{
	// 缓存探测器像素数量（避免每次事件都查询）
	const auto detConstruction = static_cast<const DetectorConstruction*>(
		G4RunManager::GetRunManager()->GetUserDetectorConstruction());
	fDetNum = detConstruction->DetPixNum;
}

EventAction::~EventAction()
{}

void EventAction::BeginOfEventAction(const G4Event*)
{
	// 使用缓存的DetNum，避免重复查询
	// 使用memset优化数组清零（G4double是POD类型，可以安全使用）
	std::memset(EdepInCrystal, 0, fDetNum * sizeof(G4double));
	std::memset(EdepInCrystal2, 0, fDetNum * sizeof(G4double));
}

void EventAction::EndOfEventAction(const G4Event* evt)
{
	// Accumulate statistics（将每个事件的像素能量累加到 RunAction 中）
	// 使用批量更新方法减少锁竞争，提高性能
	runAction->AddEdepInCrystalBatch(EdepInCrystal, fDetNum);
	runAction->AddEdepInCrystal2Batch(EdepInCrystal2, fDetNum);

	// Print per event (modulo n)
	MyeventID = 1 + evt->GetEventID();
	//G4int printModulo = G4RunManager::GetRunManager()->GetPrintProgress();

	// G4int printModulo = 100000;
	// if ( ( printModulo > 0 ) && ( MyeventID % printModulo == 0 ) )
	// {
	// 	G4cout << "---> End of event: " << MyeventID << G4endl;
	// }
}

// ======================================================================
// 旧版实现：使用 G4AnalysisManager 填充直方图（已弃用，仅注释保留）
// ======================================================================
//
// void EventAction::EndOfEventAction(const G4Event* evt)
// {
//   // Accumulate statistics
//   auto analysisManager = G4AnalysisManager::Instance();
//
//   const auto detConstruction = static_cast<const DetectorConstruction*>(
//       G4RunManager::GetRunManager()->GetUserDetectorConstruction());
//   G4int DetNum  = detConstruction->DetPixNum;
//
//   // GGAG
//   for (G4int i = 0; i < DetNum; i++) {
//     if (EdepInCrystal[i] > 0) {
//       analysisManager->FillH1(i, EdepInCrystal[i]);
//       runAction->AddEdepInCrystal(i, EdepInCrystal[i]);
//     }
//   }
//
//   // GOS
//   for (G4int i = 0; i < DetNum; i++) {
//     if (EdepInCrystal2[i] > 0) {
//       analysisManager->FillH1(DetNum + i, EdepInCrystal2[i]);
//       runAction->AddEdepInCrystal2(i, EdepInCrystal2[i]);
//     }
//   }
//
//   MyeventID = 1 + evt->GetEventID();
// }
