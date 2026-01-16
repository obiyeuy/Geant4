#include "ActionInitialization.hh"
#include "PrimaryGeneratorAction.hh"
#include "RunAction.hh"
#include "EventAction.hh"
#include "SteppingAction.hh"
#include "G4RunManager.hh"

ActionInitialization::ActionInitialization(RunAction* runAction)
 : G4VUserActionInitialization(),
   fRunAction(runAction)
{}

void ActionInitialization::BuildForMaster() const
{
  // 在主线程中，设置共享的RunAction
  // 这个RunAction用于汇总所有线程的结果
  SetUserAction(fRunAction);
}

void ActionInitialization::Build() const
{
  // 在每个工作线程中创建用户动作类
  // 每个线程都有自己的实例，保证线程安全
  
  SetUserAction(new PrimaryGeneratorAction);
  
  // 每个线程创建自己的RunAction实例用于本地统计
  // 但共享的RunAction数据（fRunAction）会通过互斥锁保护
  SetUserAction(new RunAction());
  
  // EventAction需要访问共享的RunAction来累加能量沉积
  // 使用传入的共享RunAction实例
  EventAction* eventAction = new EventAction(fRunAction);
  SetUserAction(eventAction);
  
  SetUserAction(new SteppingAction(eventAction));
}

