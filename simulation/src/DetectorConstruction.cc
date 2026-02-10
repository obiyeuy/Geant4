

#include "DetectorConstruction.hh"
#include "G4NistManager.hh"
#include "G4Material.hh"
#include "G4MaterialTable.hh"
#include "G4Element.hh"
#include "G4ElementTable.hh"
#include "G4Box.hh"
#include "G4Sphere.hh"
#include "G4RunManager.hh"
#include "DetectorMessenger.hh"
#include "G4Tubs.hh"
#include "G4VSolid.hh"
#include "G4LogicalVolume.hh"
#include "G4ThreeVector.hh"
#include "G4PVPlacement.hh"
#include "G4VisAttributes.hh"
#include "G4LogicalBorderSurface.hh"
#include "G4OpticalSurface.hh"
#include "G4SolidStore.hh"
#include "G4SubtractionSolid.hh"
#include "G4RotationMatrix.hh"
#include "G4GeometryManager.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4GDMLParser.hh"
#include "G4RunManager.hh"
#include <fstream>
using namespace CLHEP;

DetectorConstruction::DetectorConstruction()
: G4VUserDetectorConstruction(),
 ObjShift(0),
 fLogicOre(nullptr),
 fMaterialSlabMaterial(nullptr),
 fMaterialSlabThickness(0.0),
 fPhysiMaterialSlab(nullptr),
 fLogicMaterialSlab(nullptr)
{
    ObjShift = 0.0*mm; 
    fMessenger = new DetectorMessenger(this); 
	fArmRotation = new G4RotationMatrix();
}

DetectorConstruction::~DetectorConstruction()
{ 
    delete fMessenger;
}

G4VPhysicalVolume *DetectorConstruction::Construct()
{
  // Cleanup old geometry
  G4GeometryManager::GetInstance()->OpenGeometry();
  G4PhysicalVolumeStore::GetInstance()->Clean();
  G4LogicalVolumeStore::GetInstance()->Clean();
  G4SolidStore::GetInstance()->Clean();
  
  // 重置材料板指针（几何清理后需要重置）
  fPhysiMaterialSlab = nullptr;
  fLogicMaterialSlab = nullptr;

	  // ------ Vis --------
	//
	G4VisAttributes* transgrey=new G4VisAttributes(G4Colour(0.64,0.7,0.7,0.5));
	transgrey->SetForceSolid(true);
	G4VisAttributes* colorgrey=new G4VisAttributes(G4Colour(1.0,0.0,0.0,0.1));
	transgrey->SetForceSolid(true);

	G4VisAttributes* transblue=new G4VisAttributes(G4Colour(0.01,0.98,0.9,0.3));
	transblue->SetForceSolid(true);
	G4VisAttributes* transyellow=new G4VisAttributes(G4Colour(0.8,0.9,0.1,0.9));
	transyellow->SetForceSolid(true);
	G4VisAttributes* transgreen=new G4VisAttributes(G4Colour(0.2,0.98,0.1,0.9));
	transgreen->SetForceSolid(true);
	G4VisAttributes* transred=new G4VisAttributes(G4Colour(1.0, 0.0, 0.0));
	transred->SetForceSolid(true);

	auto nistMan = G4NistManager::Instance();
	G4String name, symbol;	//a=mass of a mole;
	G4double a, z, density; //z=mean number of protons;
	G4int ncomponents, natoms;

	G4double pressure = 3.e-18 * pascal;
	G4double temperature = 2.73 * kelvin;
	density = 1.e-25 * g / cm3;

	//====================================================
	// Material definitions  材料定义
	//====================================================

	//Vacuum
	G4Material *Vacuum = new G4Material(name = "Galactic", z = 1., a = 1.01 * g / mole,
										density, kStateGas, temperature, pressure);

  // Get nist material manager
 	 G4NistManager* nist = G4NistManager::Instance();

  // ========================== ========================== ========================== ==========================//
  // ========================== ========================== ========================== ==========================//

  // ----------- Material define -----------
  //  

  G4bool isotopes = false;

  G4Element *Lu = nist->FindOrBuildElement("Lu", isotopes);
  G4Element *Y = nist->FindOrBuildElement("Y", isotopes);
  G4Element *N = nist->FindOrBuildElement("N", isotopes);
  G4Element *O = nist->FindOrBuildElement("O", isotopes);
  G4Element *S = nist->FindOrBuildElement("S", isotopes);
  G4Element *Si = nist->FindOrBuildElement("Si", isotopes);
  G4Element *Ce = nist->FindOrBuildElement("Ce", isotopes);

  //
  // ==== 材料定义 ====
  //
	//-----CsI晶体------
    G4Element* elCs = nist->FindOrBuildElement("Cs");
    G4Element* elI = nist->FindOrBuildElement("I");
  	G4Material *mTl = nistMan->FindOrBuildMaterial("G4_Tl");

    density = 4.51 * g/cm3;      // CsI晶体 密度

    G4Material* CsI = new G4Material("CsI", density, ncomponents = 2);
    CsI->AddElement(elCs, 1);
    CsI->AddElement(elI, 1);
    G4Material* mCsI = new G4Material("CsI(Tl)", density, ncomponents = 2);
    G4double tlFraction = 0.001;
    mCsI->AddMaterial(CsI,  0.999);
    mCsI->AddMaterial(mTl, 0.001);

  	G4Material *mAu = nistMan->FindOrBuildMaterial("G4_Au");
  	G4Material *mPb = nistMan->FindOrBuildMaterial("G4_Pb");
  	G4Material *mW = nistMan->FindOrBuildMaterial("G4_W");
  	G4Material *mCu = nistMan->FindOrBuildMaterial("G4_Cu");
  	G4Material *mAir = nistMan->FindOrBuildMaterial("G4_AIR");
  	G4Material *mAl = nistMan->FindOrBuildMaterial("G4_Al");

    // 从NIST数据库获取元素
    G4Element* elGd = nistMan->FindOrBuildElement("Gd");
    G4Element* elGa = nistMan->FindOrBuildElement("Ga");
    G4Element* elAl = nistMan->FindOrBuildElement("Al");
    G4Element* elO  = nistMan->FindOrBuildElement("O");
    G4Element* elS  = nistMan->FindOrBuildElement("S");
	
    // 定义GGAG材料
    density = 6.63 * g/cm3;
    G4Material* GGAG = new G4Material("GGAG", density, 4);
    GGAG->AddElement(elGd, 3);
    GGAG->AddElement(elGa, 2);
    GGAG->AddElement(elAl, 3);
    GGAG->AddElement(elO,  12);

    // 定义 Gd2O2S 材料
    // density = 2.9 * g/cm3; // GOS 密度
    density = 7.34 * g/cm3; // GOS 密度
    G4Material* GOS = new G4Material("GOS", density, 3);
    GOS->AddElement(elGd, 2);
    GOS->AddElement(elO, 2);
    GOS->AddElement(elS, 1);

    // 定义元素
    G4Element* elCa = nist->FindOrBuildElement("Ca");
    G4Element* elP  = nist->FindOrBuildElement("P");

    // 定义磷酸钙（Ca3(PO4)2）
    // 注意：如果材质将从 GDML 加载，这里先不创建，避免重复定义警告
    // GDML 加载会在 LoadOreGDML() 中完成，材质会从 GDML 中读取
    // 如果 GDML 中没有定义材质，则在这里创建
    G4Material* calciumPhosphate = G4Material::GetMaterial("CalciumPhosphate");
    if (calciumPhosphate == nullptr) {
        // 材质不存在，创建它（用于默认球体）
        calciumPhosphate = new G4Material("CalciumPhosphate", 2.9 * g/cm3, 3);
        calciumPhosphate->AddElement(elCa, 3);
        calciumPhosphate->AddElement(elP,  2);
        calciumPhosphate->AddElement(elO,  8);
    }
    // 如果材质已存在（可能从之前的运行中创建），直接使用它

	//====================================================
	// Detector geometry 探测器几何构建
	//====================================================


	// 探测器晶体
	G4double Distance_Object2GGAG = 92 *mm;  // 探测器到待测物体距离
	G4double Distance_GGAG2Copper = 0.5 *mm;  // 探测器到铜距离
	G4double Distance_Copper2GOS = 3 *mm;  // GOS到铜距离

	G4int NPx = DetPixNum; //        // 晶体阵列数量，在DetectionConstruction.hh   /   RunAction.hh   /   EventAction.hh中修改

	G4double GOSlength =  0.72 *mm;
	G4double GOSwidth=  2.2 *mm;
	// G4double GOSthickness=  0.5 *mm;
    G4double GOSthickness=  0.14 *mm;

	G4double GGAGlength =  0.72 *mm;
	G4double GGAGwidth=  2.1 *mm;
	// G4double GGAGthickness=  3.3 *mm;
	G4double GGAGthickness=  4.0 *mm;
	G4double GapPeriod=  0.8 * mm; // 像素间距

	// GOS薄膜的尺寸是102.5mmX2.2mmX0.5mm
    // 高能闪烁体GGAG尺寸是102.5mmX2.1mmX3.3mm

	G4double Copperlength = 102.5 *mm;
	G4double Copperthickness = 0.6 *mm;
	// G4double Copperthickness = 1.8 *mm;

	// 待测物体
	// G4double Angle = 45;                    // 旋转角度单位 degree
    G4double sphereRadius = 15 * mm;  // 待测物半径
	//
	// ===== Detector =====


	auto solidGOS = new G4Box("solidGOS", GOSlength/2.0, GOSwidth/2.0, GOSthickness/2.0);
	auto logicGOS= new G4LogicalVolume(solidGOS, GOS, "logicGOS");

	auto solidGAGG= new G4Box("solidGAGG", GGAGlength/2.0, GGAGwidth/2.0, GGAGthickness/2.0);
	auto logicGGAG= new G4LogicalVolume(solidGAGG, GGAG, "logicGGAG");

	auto solidCopper= new G4Box("solidCopper", Copperlength/2.0, Copperlength/2.0, Copperthickness/2.0);
	auto logicCopper= new G4LogicalVolume(solidCopper, mCu, "logicCopper");

	//     
	// World
	//

	auto worldSizeXY = 10 * m;
	auto worldSizeZ  = 10 * m; 

	auto solidWorld 
		= new G4Box("World",           // its name
					worldSizeXY/2, worldSizeXY/2, worldSizeZ/2); // its size
							
	auto logicWorld
		= new G4LogicalVolume(
					solidWorld,           // its solid
					Vacuum,  // its material
					"World");         // its name
									
	auto physiWorld
		= new G4PVPlacement(
					0,                // no rotation
					G4ThreeVector(),  // at (0,0,0)
					logicWorld,          // its logical volume                         
					"Worldphys",          // its name
					0,                // its mother  volume
					false,            // no boolean operation
					0,                // copy number
					0);  // checking overlaps 

	auto Copper_phys = new G4PVPlacement(0, G4ThreeVector(0, 0,   Distance_Object2GGAG - GGAGthickness/2.0 - Copperthickness/2.0 - Distance_GGAG2Copper ), logicCopper, "Copper_phys", logicWorld,false, 0);

		// 像素探测器阵列
		for(G4int i = 0; i < NPx; i++)
		{
			G4int x_direction = NPx/2;  
			G4double Posx_shift = -(x_direction-i)*GapPeriod + GapPeriod/2.0;

			auto GGAG_phys = new G4PVPlacement(0, G4ThreeVector(Posx_shift, 0,   Distance_Object2GGAG ), logicGGAG, "GGAG_phys", logicWorld,false, i);
			auto GOS_phys = new G4PVPlacement(0, G4ThreeVector(Posx_shift, 0,   Distance_Object2GGAG - GGAGthickness/2.0 - Copperthickness- GOSthickness/2.0 			
			- Distance_GGAG2Copper - Distance_Copper2GOS ), logicGOS, "GOS_phys", logicWorld,false, i);
		}

 
    fArmRotation->rotateY(0 *deg);

    // // 待测物体 - 默认创建一个占位球体，后续可通过 GDML 动态替换
  	// auto solidObject = new G4Sphere("Object", 0., sphereRadius, 0., 360.*deg, 0., 180.*deg);
	// auto logicObject = new G4LogicalVolume(solidObject, calciumPhosphate, "logicObject");
	// // auto logicObject = new G4LogicalVolume(solidObject, Vacuum, "logicObject");

	// // 保存逻辑体积指针，用于后续动态替换
	// fLogicOre = logicObject;
	
	// // auto Object_phys = new G4PVPlacement(fArmRotation, G4ThreeVector(0,ObjShift,0), logicObject, "Object_phys", logicWorld,false,0);
    // logicObject->SetVisAttributes(transblue);
	// fPhysiObject = new G4PVPlacement(
	// 	fArmRotation, 
	// 	G4ThreeVector(0, ObjShift, 0), // 初始位置
	// 	logicObject, 
	// 	"Object_phys", 
	// 	logicWorld, 
	// 	false, 
	// 	0);
	
	                                      
	// 材料板（用于材料厚度扫描）
	// 材料板位置：在待测物体和探测器之间
	G4double MaterialSlabSizeXY = 200 * mm;  // 材料板尺寸，足够大以覆盖探测器
	G4double MaterialSlabZ = 0.0;  // 材料板中心位置，在待测物体和探测器之间
	
	// 如果材料板材料已设置，创建材料板
	if (fMaterialSlabMaterial != nullptr && fMaterialSlabThickness > 0.0) {
		auto solidMaterialSlab = new G4Box("solidMaterialSlab", 
			MaterialSlabSizeXY/2.0, MaterialSlabSizeXY/2.0, fMaterialSlabThickness/2.0);
		fLogicMaterialSlab = new G4LogicalVolume(solidMaterialSlab, fMaterialSlabMaterial, "logicMaterialSlab");
		
		// 材料板位置：在待测物体和探测器之间，距离探测器约一半距离
		fPhysiMaterialSlab = new G4PVPlacement(
			0,  // 无旋转
			G4ThreeVector(0, 0, 0),  // 位置
			fLogicMaterialSlab,
			"MaterialSlab_phys",
			logicWorld,
			false,
			0);
		
		// 设置可视化属性
		G4VisAttributes* transorange = new G4VisAttributes(G4Colour(1.0, 0.65, 0.0, 0.5));
		transorange->SetForceSolid(true);
		fLogicMaterialSlab->SetVisAttributes(transorange);
	}
	
	// Visualization attributes
	//
	logicWorld->SetVisAttributes (G4VisAttributes::GetInvisible());
	logicCopper->SetVisAttributes(transyellow);
	logicGGAG->SetVisAttributes(transgreen);
	logicGOS->SetVisAttributes(transgrey);

	// 几何优化：关闭几何并优化导航结构（提高运行时性能）
	// G4GeometryManager::GetInstance()->CloseGeometry();
	// G4GeometryManager::GetInstance()->OptimizeGeometry();

  return physiWorld;
}


void DetectorConstruction::SetObjShiftDistance(G4double shift)
{
  	ObjShift = shift;

    if (fPhysiObject) {
        // 1. 真正修改内存中物理卷的坐标
        fPhysiObject->SetTranslation(G4ThreeVector(0, ObjShift, 0));
        
        // 2. 告诉 Geant4 几何已经变了，需要重新优化导航
        // 注意：在多线程模式下，GeometryHasBeenModified() 会触发所有线程的几何重新优化
        // 如果频繁调用（如循环扫描），可能会影响性能
        // 可以考虑批量更新或延迟优化
        G4RunManager::GetRunManager()->GeometryHasBeenModified();
        
        // 可选：减少输出以提高性能（如果不需要每次位移都打印）
        // G4cout << "##### ----> The object shift distance is  " << shift << " mm  #####" << G4endl;
    } else {
        G4cout << "警告：球体物理卷尚未创建！" << G4endl;
    }
}

void DetectorConstruction::LoadOreGDML(G4String filename)
{
    G4cout << "##### Loading GDML file: " << filename << " #####" << G4endl;
    
    // 检查文件是否存在
    std::ifstream test_file(filename);
    if (!test_file.good()) {
        G4cerr << "错误：GDML 文件不存在或无法读取: " << filename << G4endl;
        return;
    }
    test_file.close();
    
    // 读取 GDML 文件（false 表示不验证 schema）
    fParser.Read(filename, false);
    
    // 从 GDML 中获取名为 "OreLog" 的逻辑体积（与 Python 约定一致）
    G4LogicalVolume* oreLog = fParser.GetVolume("OreLog");
    
    if (oreLog == nullptr) {
        G4cerr << "错误：在 GDML 文件中未找到名为 'OreLog' 的逻辑体积！" << G4endl;
        G4cerr << "提示：请确保 Python 脚本生成的 GDML 中逻辑体积名称为 'OreLog'" << G4endl;
        return;
    }
    
    // 更新物理体积的逻辑体积指针
    if (fPhysiObject != nullptr) {
        // 更新逻辑体积指针
        fLogicOre = oreLog;
        
        // 设置新的逻辑体积到物理体积
        fPhysiObject->SetLogicalVolume(oreLog);
        
        // 设置可视化属性（保持与默认一致）
        G4VisAttributes* transblue = new G4VisAttributes(G4Colour(0.01, 0.98, 0.9, 0.3));
        transblue->SetForceSolid(true);
        oreLog->SetVisAttributes(transblue);
        
        // 通知 Geant4 几何已修改，需要重新优化导航
        G4RunManager::GetRunManager()->GeometryHasBeenModified();
        
        G4cout << "##### GDML 矿石几何加载成功！#####" << G4endl;
        G4cout << "##### 逻辑体积名称: " << oreLog->GetName() << " #####" << G4endl;
    } else {
        G4cerr << "错误：物理体积 fPhysiObject 尚未创建！" << G4endl;
        G4cerr << "提示：LoadOreGDML 必须在 /run/initialize 之后调用" << G4endl;
    }
}

void DetectorConstruction::SetMaterialSlabMaterial(G4String materialName)
{
    // 从NIST数据库查找或构建材料
    auto nist = G4NistManager::Instance();
    G4Material* material = nullptr;
    
    // 处理特殊材料名称
    if (materialName == "H2O" || materialName == "Water") {
        material = nist->FindOrBuildMaterial("G4_WATER");
    } else if (materialName == "CHO" || materialName == "PMMA" || materialName == "Acrylic") {
        // 亚克力 (PMMA: C5H8O2)
        G4Element* elC = nist->FindOrBuildElement("C");
        G4Element* elH = nist->FindOrBuildElement("H");
        G4Element* elO = nist->FindOrBuildElement("O");
        G4double density = 1.19 * g/cm3;
        material = new G4Material("PMMA", density, 3);
        material->AddElement(elC, 5);
        material->AddElement(elH, 8);
        material->AddElement(elO, 2);
    } else if (materialName == "C" || materialName == "Graphite") {
        material = nist->FindOrBuildMaterial("G4_GRAPHITE");
    } else if (materialName == "Al" || materialName == "Aluminum") {
        material = nist->FindOrBuildMaterial("G4_Al");
    } else if (materialName == "Fe" || materialName == "Iron") {
        material = nist->FindOrBuildMaterial("G4_Fe");
    } else if (materialName == "Cu" || materialName == "Copper") {
        material = nist->FindOrBuildMaterial("G4_Cu");
    } else if (materialName == "Pb" || materialName == "Lead") {
        material = nist->FindOrBuildMaterial("G4_Pb");
    } else {
        // 尝试直接查找
        material = nist->FindOrBuildMaterial(materialName);
    }
    
    if (material != nullptr) {
        fMaterialSlabMaterial = material;
        G4cout << "##### 材料板材料设置为: " << material->GetName() << " #####" << G4endl;
        
        // 如果几何已构建，更新材料板
        if (fLogicMaterialSlab != nullptr) {
            fLogicMaterialSlab->SetMaterial(material);
            G4RunManager::GetRunManager()->PhysicsHasBeenModified();
        }
    } else {
        G4cerr << "错误：无法找到或创建材料: " << materialName << G4endl;
    }
}

void DetectorConstruction::SetMaterialSlabThickness(G4double thickness)
{
    fMaterialSlabThickness = thickness;
    G4cout << "##### 材料板厚度设置为: " << thickness / mm << " mm #####" << G4endl;
    
    // 如果几何已构建，通知需要重新初始化几何
    // 注意：在 /run/initialize 之前设置厚度时，会在 Construct() 中创建
    // 在 /run/initialize 之后设置厚度时，需要重新初始化几何
    if (fPhysiMaterialSlab != nullptr) {
        // 几何已构建，需要重新初始化
        // 注意：这会触发完整的几何重建，包括 Construct() 的重新调用
        G4RunManager::GetRunManager()->ReinitializeGeometry();
    }
}
