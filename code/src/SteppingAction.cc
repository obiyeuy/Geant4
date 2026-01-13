#include "SteppingAction.hh"
#include "EventAction.hh"
#include "G4SteppingManager.hh"
#include "DetectorConstruction.hh"
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "G4RunManager.hh"
#include "fstream"
#include "iomanip"

using namespace std;	 

SteppingAction::SteppingAction(EventAction* EvAct)
:eventAction(EvAct)
{ }

SteppingAction::~SteppingAction()
{ }

void SteppingAction::UserSteppingAction(const G4Step* aStep)
{
	auto aTrack = aStep ->GetTrack();
	//const G4TrackVector* fpTrackVector = fpStep ->GetTrackStatus();//G4TrackVector.hh矢量定义fpTrackVector
	//G4TrackStatus TrackStatus = fpTrack -> GetSecondary();//G4TrackStatus.hh态
	auto fpPreStepPoint = aStep ->GetPreStepPoint();//步的前点
	auto fpPostStepPoint = aStep ->GetPostStepPoint();//步的后点
	G4String matname=fpPreStepPoint->GetMaterial()->GetName();

	G4int EvtID = eventAction->MyeventID;

	G4String postVolume = "NULL";
	G4String preVolume = "NULL_pre";

	if(aTrack ->GetNextVolume())//判断粒子是否在世界里
	{
		postVolume = fpPostStepPoint ->GetPhysicalVolume() ->GetName();//获取粒子所在体的名字并赋给volume，用于判断粒子位置
		preVolume = fpPreStepPoint ->GetPhysicalVolume() ->GetName();
	}

	const G4String particleName
	= aStep->GetTrack()->GetDefinition()->GetParticleName();

	const auto detConstruction = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;


	if (matname == "GOS"  ){
		// if ( particleName=="gamma"  && postVolume == "GGAG_phys" &&  fpPostStepPoint->GetStepStatus()==fGeomBoundary) {
		G4double EdepStep = aStep->GetTotalEnergyDeposit()/keV;	
		// G4double EdepStep = fpPreStepPoint->GetKineticEnergy()/keV;
		// cout<<"xx"<<endl;
		if(EdepStep>0)
		{
			//fstream datafile;
			//datafile.open("Datalist.txt",ios::out|ios::app);//NeutronballAngleDistribution.txt
			G4int CopyNum = fpPreStepPoint->GetTouchable()->GetCopyNumber();
			//GetTouchableHandle()->GetCopyNumber();
			G4int CoNo =  (CopyNum)%DetNum;
			// cout<<CoNo<<endl;
			eventAction->EdepInCrystal2[CoNo] +=EdepStep;


		}

			
	}


	if (matname == "GGAG"  ){
		// if ( particleName=="gamma"  && postVolume == "GGAG_phys" &&  fpPostStepPoint->GetStepStatus()==fGeomBoundary) {
		G4double EdepStep = aStep->GetTotalEnergyDeposit()/keV;	
		// G4double EdepStep = fpPreStepPoint->GetKineticEnergy()/keV;
		// cout<<"xx"<<endl;
		if(EdepStep>0)
		{
			//fstream datafile;
			//datafile.open("Datalist.txt",ios::out|ios::app);//NeutronballAngleDistribution.txt
			G4int CopyNum = fpPreStepPoint->GetTouchable()->GetCopyNumber();
			//GetTouchableHandle()->GetCopyNumber();
			G4int CoNo =  (CopyNum)%DetNum;
			// cout<<CoNo<<endl;
			eventAction->EdepInCrystal[CoNo] +=EdepStep;


		}

			
	}

}

