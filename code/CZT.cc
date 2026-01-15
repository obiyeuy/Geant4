/////////////////////////////////////////////////////////
//                                                     //
//  Oct/2013  E. Nacher  -->  main.cc                  //
//  Practical work for the SWG2013 Workshop            //
//                                                     //
/////////////////////////////////////////////////////////

#include "G4RunManagerFactory.hh"
#include "G4MTRunManager.hh"
#include "G4UImanager.hh"
#include "G4UIterminal.hh"

#ifdef G4UI_USE_TCSH
#include "G4UItcsh.hh"
#endif

#include "DetectorConstruction.hh"
#include "PhysicsList.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "EventAction.hh"
#include "SteppingAction.hh"
#include "ActionInitialization.hh"

//#ifdef G4VIS_USE
#include "G4VisExecutive.hh"
//#endif

//#ifdef G4UI_USE
#include "G4UIExecutive.hh"
//#endif

#include "Randomize.hh"
#include "globals.hh"

#include "G4ios.hh"
#include "fstream"
#include "iomanip"

#include <fstream>
#include <cstdlib>  // for std::getenv and std::atoi

using namespace std;	 

int main(int argc, char** argv)
{
  // 每次运行使用不同种子
  std::ifstream urandom("/dev/urandom", std::ios::in | std::ios::binary);
  long seed;
  urandom.read(reinterpret_cast<char*>(&seed), sizeof(seed));
  G4Random::setTheSeed(std::abs(seed));
  
  urandom.close();
	
	// 创建多线程运行管理器
	// 可以通过环境变量 G4FORCENUMBEROFTHREADS 或命令行参数设置线程数
	// 默认使用系统可用核心数
	G4MTRunManager* runManager = G4MTRunManager::GetMasterRunManager();
	if (runManager == nullptr) {
		runManager = new G4MTRunManager;
	}
	
	// 设置线程数（可以通过环境变量 G4FORCENUMBEROFTHREADS 设置）
	// 如果没有设置，Geant4会自动检测CPU核心数
	G4int nThreads = 0;  // 0表示自动检测
	const char* envThreads = std::getenv("G4FORCENUMBEROFTHREADS");
	if (envThreads != nullptr) {
		nThreads = std::atoi(envThreads);
	}
	if (nThreads > 0) {
		runManager->SetNumberOfThreads(nThreads);
		G4cout << "Using " << nThreads << " threads" << G4endl;
	} else {
		G4cout << "Using automatic thread detection" << G4endl;
	}
	
	// set mandatory initialization classes
	runManager->SetUserInitialization(new DetectorConstruction);
	runManager->SetUserInitialization(new PhysicsList);
		
	// set aditional user action classes
	// 在多线程模式下，创建一个共享的RunAction实例用于汇总结果
	// ActionInitialization会在每个线程中创建自己的用户动作类实例
	RunAction* sharedRunAction = new RunAction;
	runManager->SetUserInitialization(new ActionInitialization(sharedRunAction));
	
	// 只在交互模式（直接运行 ./CZT 而不带宏文件）下初始化可视化
	// batch 模式（例如 ./CZT master.mac）不创建可视化，以减少开销
	G4VisManager* visManager = nullptr;
	if (argc == 1) {
	  // Initialize visualization
	  visManager = new G4VisExecutive;
	  // G4VisExecutive can take a verbosity argument - see /vis/verbose guidance.
	  // G4VisManager* visManager = new G4VisExecutive("Quiet");
	  visManager->Initialize();
	}
  // initialize G4 kernel
  // runManager->Initialize();
  
  // 注意：在多线程模式下，用户动作类通过ActionInitialization设置
  // 不需要在这里单独设置PrimaryGeneratorAction

  // Get the pointer to the User Interface manager
  G4UImanager* UImanager = G4UImanager::GetUIpointer();

  if (argc!=1) {
    // batch mode
    G4String command = "/control/execute ";
    G4String fileName = argv[1];
    UImanager->ApplyCommand(command+fileName);
  }
  else {
    // interactive mode : define UI session
//#ifdef G4UI_USE
    G4UIExecutive* ui = new G4UIExecutive(argc, argv);
//#ifdef G4VIS_USE
    UImanager->ApplyCommand("/control/execute init_vis.mac"); 
//#else
    UImanager->ApplyCommand("/control/execute init.mac"); 
//#endif
    ui->SessionStart();
    delete ui;
//#endif
  }

  // Job termination
  // Free the store: user actions, physics_list and detector_description are
  // owned and deleted by the run manager, so they should not be deleted 
  // in the main() program !
  
  if (visManager) {
    delete visManager;
  }
  delete runManager;

  return 0;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo.....
