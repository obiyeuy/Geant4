

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
using namespace CLHEP;

DetectorConstruction::DetectorConstruction()
: G4VUserDetectorConstruction(),
 ObjShift(0)
{
    ObjShift = 0.0*mm; 
    fMessenger = new DetectorMessenger(this); 
	fArmRotation = new G4RotationMatrix();
}

DetectorConstruction::~DetectorConstruction()
{ delete fMessenger;
}

G4VPhysicalVolume *DetectorConstruction::Construct()
{
  // Cleanup old geometry
  G4GeometryManager::GetInstance()->OpenGeometry();
  G4PhysicalVolumeStore::GetInstance()->Clean();
  G4LogicalVolumeStore::GetInstance()->Clean();
  G4SolidStore::GetInstance()->Clean();

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
    density = 2.9 * g/cm3; // GOS 密度
    G4Material* GOS = new G4Material("GOS", density, 3);
    GOS->AddElement(elGd, 2);
    GOS->AddElement(elO, 2);
    GOS->AddElement(elS, 1);

    // 定义元素
    G4Element* elCa = nist->FindOrBuildElement("Ca");
    G4Element* elP  = nist->FindOrBuildElement("P");

    // 定义磷酸钙（Ca3(PO4)2）
    G4Material* calciumPhosphate = new G4Material("CalciumPhosphate", 2.9 * g/cm3, 3);
    calciumPhosphate->AddElement(elCa, 3);
    calciumPhosphate->AddElement(elP,  2);
    calciumPhosphate->AddElement(elO,  8);

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
	G4double GOSthickness=  0.5 *mm;

	G4double GGAGlength =  0.72 *mm;
	G4double GGAGwidth=  2.1 *mm;
	G4double GGAGthickness=  3.3 *mm;
	G4double GapPeriod=  0.8 * mm; // 像素间距

	// GOS薄膜的尺寸是102.5mmX2.2mmX0.5mm
    // 高能闪烁体GGAG尺寸是102.5mmX2.1mmX3.3mm

	G4double Copperlength = 102.5 *mm;
	G4double Copperthickness = 0.6 *mm;
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

    //待测物体
  	auto solidObject = new G4Sphere("Object", 0., sphereRadius, 0., 360.*deg, 0., 180.*deg);
	// auto logicObject = new G4LogicalVolume(solidObject, calciumPhosphate, "logicObject");
	auto logicObject = new G4LogicalVolume(solidObject, Vacuum, "logicObject");

	// auto Object_phys = new G4PVPlacement(fArmRotation, G4ThreeVector(0,ObjShift,0), logicObject, "Object_phys", logicWorld,false,0);
    logicObject->SetVisAttributes(transblue);
	fPhysiObject = new G4PVPlacement(
		fArmRotation, 
		G4ThreeVector(0, ObjShift, 0), // 初始位置
		logicObject, 
		"Object_phys", 
		logicWorld, 
		false, 
		0);
	
	//                                        
	// Visualization attributes
	//
	logicWorld->SetVisAttributes (G4VisAttributes::GetInvisible());
	logicCopper->SetVisAttributes(transyellow);
	logicGGAG->SetVisAttributes(transgreen);
	logicObject->SetVisAttributes(transblue);
	logicGOS->SetVisAttributes(transgrey);

  return physiWorld;
}


void DetectorConstruction::SetObjShiftDistance(G4double shift)
{

  	G4cout
          << G4endl 
          << "##### ----> The object shift distance is  " << shift << " mm  #####" << G4endl;
  	ObjShift = shift;
	
  	// // G4RunManager::GetRunManager()->PhysicsHasBeenModified();
	// G4RunManager::GetRunManager()->GeometryHasBeenModified();
	// ObjShift = shift;
    // G4cout << "##### ----> 正在搬动球体到 Y = " << shift << " mm #####" << G4endl;

    if (fPhysiObject) {
        // 1. 真正修改内存中物理卷的坐标
        fPhysiObject->SetTranslation(G4ThreeVector(0, ObjShift, 0));
        
        // 2. 告诉 Geant4 几何已经变了，需要重新优化导航（必写）
        G4RunManager::GetRunManager()->GeometryHasBeenModified();
    } else {
        G4cout << "警告：球体物理卷尚未创建！" << G4endl;
    }
}
