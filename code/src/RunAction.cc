
#include "RunAction.hh"
// #include "Analysis.hh"
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4SystemOfUnits.hh"
#include "DetectorConstruction.hh"
#include "G4Run.hh"
#include "G4ios.hh"
#include "G4Threading.hh"
// 旧版输出依赖的头文件（保留作参考，已不再使用）
// #include "G4AnalysisManager.hh"
#include <iomanip>
#include <sstream>
#include <sys/stat.h>
#include <sys/types.h>

// 静态成员变量定义
std::mutex RunAction::fEdepMutex;
std::mutex RunAction::fEdepMutex2;

RunAction::RunAction() : G4UserRunAction()
{
	const auto detConstruction = static_cast<const DetectorConstruction*>(
	    G4RunManager::GetRunManager()->GetUserDetectorConstruction());

	fDetNum = detConstruction->DetPixNum;

  	G4RunManager::GetRunManager()->SetPrintProgress(1000);

	// 初始化本 run 的累加数组
	for(G4int i = 0; i < fDetNum; i++)
	{
		Run_EdepInCrystal[i]  = 0.0;	
		Run_EdepInCrystal2[i] = 0.0;	
	}	
}

void RunAction::BeginOfRunAction(const G4Run*)
{
	  //inform the runManager to save random number seed
	  //G4RunManager::GetRunManager()->SetRandomNumberStore(true);

	// 关键：如果在同一个进程里多次 /run/beamOn（例如用 /control/loop 扫描），
	// Run_EdepInCrystal 会跨"run"累加，导致后处理图像出现条纹/渐增等伪影。
	// 因此每个 run 开始时都要清零一次（线程安全）。
	// 使用缓存的DetNum，避免重复查询
	{
		std::lock_guard<std::mutex> lock1(fEdepMutex);
		std::lock_guard<std::mutex> lock2(fEdepMutex2);
		for (G4int i = 0; i < fDetNum; i++) {
			Run_EdepInCrystal[i] = 0.0;
			Run_EdepInCrystal2[i] = 0.0;
		}
	}

	// 检查是否是主线程（在多线程模式下，只有主线程执行目录创建等操作）
	// 在单线程模式下，isMaster 始终为 true
	if (isMaster) {
		// 输出基础目录名
		G4String outputDir = "output";
		
		// 为每种文件类型创建各自的文件夹
		G4String dirListMode1 = outputDir + "/LowEnergy";
		G4String dirListMode2 = outputDir + "/HighEnergy";
		
		// 创建各个输出目录（如果不存在）
		mkdir(outputDir.c_str(), 0755);
		mkdir(dirListMode1.c_str(), 0755);
		mkdir(dirListMode2.c_str(), 0755);
	}
}

void RunAction::EndOfRunAction(const G4Run*)
{
	// 仅在主线程输出结果到二进制文件
	if (isMaster) {
		const auto detConstruction = static_cast<const DetectorConstruction*>(
		      G4RunManager::GetRunManager()->GetUserDetectorConstruction());
		  
		// 输出基础目录名（与 BeginOfRunAction 中保持一致）
		G4String outputDir = "output";
		  
		// 为每种文件类型创建各自的文件夹
		G4String dirListMode1 = outputDir + "/LowEnergy";
		G4String dirListMode2 = outputDir + "/HighEnergy";
		  
		// 获取 ObjShift 值用于生成文件名
		G4double objShift = detConstruction->GetObjShiftDistance();
		  
		// 将 ObjShift 值转换为字符串，用于文件名
		std::stringstream ss;
		ss << std::fixed << std::setprecision(1) << objShift;
		G4String objShiftStr = ss.str();
		  
		// 生成带各自目录和 ObjShift 值的文件路径（后缀改为 .bin）
		G4String fileName1 = dirListMode1 + "/" + objShiftStr + ".bin";
		G4String fileName2 = dirListMode2 + "/" + objShiftStr + ".bin";

		// 写入低能量阵列（GGAG）到二进制文件
		std::ofstream datafile1(fileName1, std::ios::binary | std::ios::trunc);
		if (datafile1.is_open()) {
			datafile1.write(
				reinterpret_cast<const char*>(Run_EdepInCrystal),
				static_cast<std::streamsize>(fDetNum) * sizeof(G4double));
			datafile1.close();
		} else {
			G4cerr << "Error opening file for write: " << fileName1 << G4endl;
		}

		// 写入高能量阵列（GOS）到二进制文件
		std::ofstream datafile2(fileName2, std::ios::binary | std::ios::trunc);
		if (datafile2.is_open()) {
			datafile2.write(
				reinterpret_cast<const char*>(Run_EdepInCrystal2),
				static_cast<std::streamsize>(fDetNum) * sizeof(G4double));
			datafile2.close();
		} else {
			G4cerr << "Error opening file for write: " << fileName2 << G4endl;
		}
	}
}

void RunAction::AddEdepInCrystal(G4int index, G4double edep)
{
  // 使用互斥锁保护共享数据的累加操作
  std::lock_guard<std::mutex> lock(fEdepMutex);
  Run_EdepInCrystal[index] += edep;
}

void RunAction::AddEdepInCrystal2(G4int index, G4double edep)
{
  // 使用互斥锁保护共享数据的累加操作
  std::lock_guard<std::mutex> lock(fEdepMutex2);
  Run_EdepInCrystal2[index] += edep;
}

void RunAction::AddEdepInCrystalBatch(const G4double* edepArray, G4int size)
{
  // 批量更新：一次获取锁，更新所有像素，减少锁竞争
  // 注意：edepArray中的值已经在EventAction中检查过>0，这里直接累加
  std::lock_guard<std::mutex> lock(fEdepMutex);
  for (G4int i = 0; i < size; i++) {
    Run_EdepInCrystal[i] += edepArray[i];
  }
}

void RunAction::AddEdepInCrystal2Batch(const G4double* edepArray, G4int size)
{
  // 批量更新：一次获取锁，更新所有像素，减少锁竞争
  // 注意：edepArray中的值已经在EventAction中检查过>0，这里直接累加
  std::lock_guard<std::mutex> lock(fEdepMutex2);
  for (G4int i = 0; i < size; i++) {
    Run_EdepInCrystal2[i] += edepArray[i];
  }
}

// ======================================================================
// 旧版实现：使用 G4AnalysisManager + txt/root 输出（已弃用，仅注释保留）
// ======================================================================
//
// 下面这段是之前版本的 BeginOfRunAction / EndOfRunAction 主要逻辑，
// 为了方便以后对比或恢复，这里用注释的形式完整保留：
//
// void RunAction::BeginOfRunAction(const G4Run*)
// {
//   //inform the runManager to save random number seed
//   //G4RunManager::GetRunManager()->SetRandomNumberStore(true);
//
//   // 清零 Run_EdepInCrystal / Run_EdepInCrystal2
//   {
//     const auto detConstruction = static_cast<const DetectorConstruction*>(
//         G4RunManager::GetRunManager()->GetUserDetectorConstruction());
//     G4int DetNum = detConstruction->DetPixNum;
//
//     std::lock_guard<std::mutex> lock1(fEdepMutex);
//     std::lock_guard<std::mutex> lock2(fEdepMutex2);
//     for (G4int i = 0; i < DetNum; i++) {
//       Run_EdepInCrystal[i] = 0.0;
//       Run_EdepInCrystal2[i] = 0.0;
//     }
//   }
//
//   if (isMaster) {
//     G4String outputDir = "output";
//     G4String dirListMode1 = outputDir + "/LowEnergy";
//     G4String dirListMode2 = outputDir + "/HighEnergy";
//     G4String dirMydata    = outputDir + "/Mydata";
//
//     mkdir(outputDir.c_str(), 0755);
//     mkdir(dirListMode1.c_str(), 0755);
//     mkdir(dirListMode2.c_str(), 0755);
//     mkdir(dirMydata.c_str(),   0755);
//
//     const auto detConstruction = static_cast<const DetectorConstruction*>(
//         G4RunManager::GetRunManager()->GetUserDetectorConstruction());
//     G4double objShift = detConstruction->GetObjShiftDistance();
//
//     std::stringstream ss;
//     ss << std::fixed << std::setprecision(1) << objShift;
//     G4String objShiftStr = ss.str();
//
//     G4String fileName1   = dirListMode1 + "/" + objShiftStr + ".txt";
//     G4String fileName2   = dirListMode2 + "/" + objShiftStr + ".txt";
//     G4String rootFileName = dirMydata  + "/" + objShiftStr + ".root";
//
//     // 预创建 txt 文件
//     fstream datafile1(fileName1, ios::out | ios::trunc);
//     datafile1.close();
//     fstream datafile2(fileName2, ios::out | ios::trunc);
//     datafile2.close();
//
//     // 使用 G4AnalysisManager 打开 ROOT 输出
//     auto analysisManager = G4AnalysisManager::Instance();
//     analysisManager->OpenFile(rootFileName);
//     G4cout << "Using " << analysisManager->GetType() << G4endl;
//     G4cout << "Output files with ObjShift = " << objShift << " mm" << G4endl;
//   }
// }
//
// void RunAction::EndOfRunAction(const G4Run*)
// {
//   auto analysisManager = G4AnalysisManager::Instance();
//
//   if (isMaster) {
//     analysisManager->Write();
//     analysisManager->CloseFile();
//
//     const auto detConstruction = static_cast<const DetectorConstruction*>(
//         G4RunManager::GetRunManager()->GetUserDetectorConstruction());
//
//     G4int DetNum  = detConstruction->DetPixNum;
//     G4String outputDir = "output";
//     G4String dirListMode1 = outputDir + "/LowEnergy";
//     G4String dirListMode2 = outputDir + "/HighEnergy";
//
//     G4double objShift = detConstruction->GetObjShiftDistance();
//     std::stringstream ss;
//     ss << std::fixed << std::setprecision(1) << objShift;
//     G4String objShiftStr = ss.str();
//
//     G4String fileName1 = dirListMode1 + "/" + objShiftStr + ".txt";
//     G4String fileName2 = dirListMode2 + "/" + objShiftStr + ".txt";
//
//     // 将 Run_EdepInCrystal / Run_EdepInCrystal2 写成 txt
//     fstream datafile1(fileName1, ios::out | ios::trunc);
//     for (G4int i = 0; i < DetNum; i++) {
//       datafile1 << Run_EdepInCrystal[i] << "\t";
//     }
//     datafile1.close();
//
//     fstream datafile2(fileName2, ios::out | ios::trunc);
//     for (G4int i = 0; i < DetNum; i++) {
//       datafile2 << Run_EdepInCrystal2[i] << "\t";
//     }
//     datafile2.close();
//   }
// }

