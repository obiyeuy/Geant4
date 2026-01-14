
#include "EventAction.hh"

//#include "Randomize.hh" // do we really need this?
#include <iomanip>

#include "RunAction.hh"
// #include "Analysis.hh"
#include "G4ParticleGun.hh"
#include "PrimaryGeneratorAction.hh"
#include "G4RunManager.hh"

#include "G4Event.hh"
#include "G4EventManager.hh"
#include "G4UnitsTable.hh"
#include "G4AnalysisManager.hh"
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

	// Accumulate statistics
	// get analysis manager
	  auto analysisManager = G4AnalysisManager::Instance();

	// Fill histograms
	const auto detConstruction = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;

	 for(G4int i = 0; i<DetNum; i++)
	 {
	 		if(EdepInCrystal[i]>0)
	 		{
	 			//cout<<G4double(i)<< "\t"<< G4double(j)<< "\t"<< EdepInCrystal[i][j] <<endl;
	 			analysisManager->FillH1(i,  EdepInCrystal[i]);		
				// 使用线程安全的方法累加能量沉积
				runAction->AddEdepInCrystal(i, EdepInCrystal[i]);
	 		}

	 }



	 for(G4int i = 0; i<DetNum; i++)
	 {
	 		if(EdepInCrystal2[i]>0)
	 		{
	 			//cout<<G4double(i)<< "\t"<< G4double(j)<< "\t"<< EdepInCrystal[i][j] <<endl;
	 			analysisManager->FillH1(DetNum + i,  EdepInCrystal2[i]);		
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
