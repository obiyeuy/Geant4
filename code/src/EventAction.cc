
#include "EventAction.hh"

//#include "Randomize.hh" // do we really need this?
#include <iomanip>

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
	
}

EventAction::~EventAction()
{}

void EventAction::BeginOfEventAction(const G4Event*)
{
	const auto detConstruction = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;


	 for(G4int i = 0; i<DetNum; i++)
	 {
	 		EdepInCrystal[i] = 0;
	 		EdepInCrystal2[i] = 0;
	 }
}

void EventAction::EndOfEventAction(const G4Event* evt)
{

	// Accumulate statistics（将每个事件的像素能量累加到 RunAction 中）
	const auto detConstruction = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;

	 for(G4int i = 0; i<DetNum; i++)
	 {
	 		if(EdepInCrystal[i]>0)
	 		{
				// 使用线程安全的方法累加能量沉积
				runAction->AddEdepInCrystal(i, EdepInCrystal[i]);
	 		}

	 }



	 for(G4int i = 0; i<DetNum; i++)
	 {
	 		if(EdepInCrystal2[i]>0)
	 		{
				// 使用线程安全的方法累加能量沉积
				runAction->AddEdepInCrystal2(i, EdepInCrystal2[i]);
	 		}

	 }



	// Print per event (modulo n)
	//
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
