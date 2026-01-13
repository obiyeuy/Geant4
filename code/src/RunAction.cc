
#include "RunAction.hh"
// #include "Analysis.hh"
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "DetectorConstruction.hh"
#include "G4Run.hh"
#include "G4ios.hh"
#include "G4AnalysisManager.hh"
#include <iomanip>
#include <sstream>
#include <sys/stat.h>
#include <sys/types.h>


RunAction::RunAction() : G4UserRunAction()
{
	  // Create analysis manager
	  // The choice of analysis technology is done via selecting of a namespace
	//   // in B4Analysis.hh
	const auto detConstruction = static_cast<const DetectorConstruction*>(
    G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;

  	G4RunManager::GetRunManager()->SetPrintProgress(1000);
	auto analysisManager = G4AnalysisManager::Instance();
	analysisManager->SetVerboseLevel(1);
	analysisManager->SetNtupleMerging(true);

    // analysisManager->CreateH2("EdepInCrystal","Edep", DetNum, 0, DetNum, DetNum, 0, DetNum);

	  stringstream os;  
	  G4String title= " Pixel NO. ";	
	  G4String name1, file_name;


	  for(int i = 0; i<DetNum; i++)
	  {
			os<<1000 + i;
			os>>name1;
			os.clear();

			file_name = title + name1;
			analysisManager->CreateH1(file_name,file_name, 1000, 0, 200);

	  }

	  for(int i = 0; i<DetNum; i++)
	  {
			os<<2000 + i;
			os>>name1;
			os.clear();

			file_name = title + name1;
			analysisManager->CreateH1(file_name,file_name, 1000, 0, 200);

	  }


	 for(G4int i = 0; i<DetNum; i++)
	 {
			Run_EdepInCrystal[i] = 0;	
			Run_EdepInCrystal2[i] = 0;	
	 }	


}

void RunAction::BeginOfRunAction(const G4Run*)
{
	  //inform the runManager to save random number seed
	  //G4RunManager::GetRunManager()->SetRandomNumberStore(true);

	// 输出基础目录名
	G4String outputDir = "output";
	
	// 为每种文件类型创建各自的文件夹
	G4String dirListMode1 = outputDir + "/LowEnergy";
	G4String dirListMode2 = outputDir + "/HighEnergy";
	G4String dirMydata = outputDir + "/Mydata";
	
	// 创建各个输出目录（如果不存在）
	mkdir(outputDir.c_str(), 0755);
	mkdir(dirListMode1.c_str(), 0755);
	mkdir(dirListMode2.c_str(), 0755);
	mkdir(dirMydata.c_str(), 0755);

	// 获取ObjShift值用于生成文件名
	const auto detConstruction = static_cast<const DetectorConstruction*>(
		G4RunManager::GetRunManager()->GetUserDetectorConstruction());
	G4double objShift = detConstruction->GetObjShiftDistance();
	
	// 将ObjShift值转换为字符串，用于文件名
	std::stringstream ss;
	ss << std::fixed << std::setprecision(1) << objShift;
	G4String objShiftStr = ss.str();
	
	// 生成带各自目录和ObjShift值的文件路径
	G4String fileName1 = dirListMode1 + "/" + objShiftStr + ".txt";
	G4String fileName2 = dirListMode2 + "/" + objShiftStr + ".txt";
	G4String rootFileName = dirMydata + "/" + objShiftStr + ".root";

	fstream datafile1;
	datafile1.open(fileName1,ios::out|ios::trunc);
	datafile1.close();

	fstream datafile2;
	datafile2.open(fileName2,ios::out|ios::trunc);
	datafile2.close();


	//   // Get analysis manager
	  auto analysisManager = G4AnalysisManager::Instance();

	  // Open an output file
	  //
	  analysisManager->OpenFile(rootFileName);
  	  G4cout << "Using " << analysisManager->GetType() << G4endl;
  	  G4cout << "Output files with ObjShift = " << objShift << " mm" << G4endl;
}

void RunAction::EndOfRunAction(const G4Run*)
{
	  // print histogram statistics
	  //
	  auto analysisManager = G4AnalysisManager::Instance();
	  analysisManager->Write();
	  analysisManager->CloseFile();

	const auto detConstruction = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	G4int DetNum  = detConstruction->DetPixNum;
	
	// 输出基础目录名（与BeginOfRunAction中保持一致）
	G4String outputDir = "output";
	
	// 为每种文件类型创建各自的文件夹
	G4String dirListMode1 = outputDir + "/LowEnergy";
	G4String dirListMode2 = outputDir + "/HighEnergy";
	
	// 获取ObjShift值用于生成文件名
	G4double objShift = detConstruction->GetObjShiftDistance();
	
	// 将ObjShift值转换为字符串，用于文件名
	std::stringstream ss;
	ss << std::fixed << std::setprecision(1) << objShift;
	G4String objShiftStr = ss.str();
	
	// 生成带各自目录和ObjShift值的文件路径
	G4String fileName1 = dirListMode1 + "/" + objShiftStr + ".txt";
	G4String fileName2 = dirListMode2 + "/" + objShiftStr + ".txt";

	fstream datafile1;
	datafile1.open(fileName1,ios::out|ios::trunc);

	 for(G4int i = 0; i<DetNum; i++)
	 {

			datafile1<<Run_EdepInCrystal[i]<< "\t";
	
	 }


	fstream datafile2;
	datafile2.open(fileName2,ios::out|ios::trunc);

	 for(G4int i = 0; i<DetNum; i++)
	 {

			datafile2<<Run_EdepInCrystal2[i]<< "\t";
	
	 }

	datafile1.close();
	datafile2.close();


}


