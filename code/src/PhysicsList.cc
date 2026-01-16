#include "PhysicsList.hh"

#include "G4EmStandardPhysics.hh"
#include "G4EmStandardPhysics_option4.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4EmPenelopePhysics.hh"
#include "G4ParticleTypes.hh"

#include "G4SystemOfUnits.hh"
#include "G4DecayPhysics.hh"
#include "G4RadioactiveDecayPhysics.hh"

// particles
#include "G4BosonConstructor.hh"
#include "G4LeptonConstructor.hh"
#include "G4MesonConstructor.hh"
#include "G4BosonConstructor.hh"
#include "G4BaryonConstructor.hh"
#include "G4IonConstructor.hh"
#include "G4ShortLivedConstructor.hh"

#include "G4RegionStore.hh"
#include "G4ProductionCutsTable.hh"
#include "G4ProductionCuts.hh"


PhysicsList::PhysicsList() : G4VModularPhysicsList()
{

	// Decay（对于X射线检测，通常不需要）
	// RegisterPhysics(new G4DecayPhysics());

	// Radioactive decay（对于X射线检测，不需要放射性衰变过程）
	// RegisterPhysics(new G4RadioactiveDecayPhysics());   // 已禁用以提高性能

	// EM Physics 以下四选一即可
	// 使用option4以获得更好的性能（相比option3更快，同时保持合理精度）
	RegisterPhysics(new G4EmStandardPhysics_option4());
	//RegisterPhysics(new G4EmStandardPhysics());  // 标准物理，较慢但更精确
	//RegisterPhysics(new G4EmLivermorePhysics());  // Livermore模型，较慢
	//RegisterPhysics(new G4EmPenelopePhysics());   // Penelope模型，较慢

	// Cut值选择说明：
	// - 0.01-0.03 mm: 高精度模式（推荐用于最终结果验证）
	//   优点：精确追踪所有低能次级粒子，结果最准确
	//   缺点：计算速度较慢
	// - 0.05 mm: 平衡模式（推荐用于日常模拟）
	//   优点：精度和速度的良好平衡，对20-160 keV X射线足够精确
	//   缺点：可能略微低估极低能（<30 keV）粒子的贡献
	// - 0.1 mm: 快速模式（用于快速测试或大批量扫描）
	//   优点：计算速度快，适合大规模参数扫描
	//   缺点：可能丢失部分低能粒子的能量沉积
	//
	// 当前设置：0.05 mm（平衡模式）
	// 探测器最小厚度0.5 mm，像素尺寸0.7 mm，0.05 mm约为最小尺寸的1/10，是合理选择
	SetDefaultCutValue(0.03*mm); 
}


PhysicsList::~PhysicsList() {}

void PhysicsList::SetCuts(){
	
	SetCutsWithDefault();
	
	// 可选：为不同区域设置不同的cut值以优化性能
	// 世界区域可以使用较大的cut值，探测器区域使用较小的cut值
	// 示例（如果需要可以取消注释，并添加必要的头文件）：
	// #include "G4RegionStore.hh"
	// #include "G4ProductionCutsTable.hh"
	// #include "G4ProductionCuts.hh"
	auto cutsTable = G4ProductionCutsTable::GetProductionCutsTable();
	G4Region* worldRegion = G4RegionStore::GetInstance()->GetRegion("DefaultRegionForTheWorld");
	if (worldRegion) {
	    G4ProductionCuts* worldCuts = worldRegion->GetProductionCuts();
	    if (worldCuts) {
	        worldCuts->SetProductionCut(0.1*mm, 0); // gamma
	        worldCuts->SetProductionCut(0.1*mm, 1); // e-
	        worldCuts->SetProductionCut(0.1*mm, 2); // e+
	    }
	}
}

void PhysicsList::ConstructParticle()
{
  // 对于X射线检测，需要构建必要的粒子类型
  // G4EmStandardPhysics_option4需要所有标准粒子的进程管理器
  // 虽然X射线检测主要使用gamma和电子，但物理过程会为所有粒子类型注册过程
  
  G4BosonConstructor  pBosonConstructor;
  pBosonConstructor.ConstructParticle();  // 构建gamma等玻色子

  G4LeptonConstructor pLeptonConstructor;
  pLeptonConstructor.ConstructParticle();  // 构建e-, e+等轻子

  // 介子构造器是必需的：G4EmStandardPhysics_option4需要介子（如pi+）的进程管理器
  G4MesonConstructor pMesonConstructor;
  pMesonConstructor.ConstructParticle();

  // 重子构造器是必需的：G4EmStandardPhysics_option4需要重子（如proton）的进程管理器
  G4BaryonConstructor pBaryonConstructor;
  pBaryonConstructor.ConstructParticle();

  // 离子构造器是必需的：G4EmStandardPhysics_option4需要GenericIon的进程管理器
  G4IonConstructor pIonConstructor;
  pIonConstructor.ConstructParticle();

  // 短寿命粒子通常不需要，已禁用以提高初始化速度
  // G4ShortLivedConstructor pShortLivedConstructor;
  // pShortLivedConstructor.ConstructParticle();  
}
