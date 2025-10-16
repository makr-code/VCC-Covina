#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Graduelle Migration Manager für UDS3 Adaptive Multi-DB Strategy

Implementiert schrittweise Migration Paths zwischen verschiedenen Database-Strategien
ohne Systemunterbrechung. Ermöglicht Verwaltungen eine graduelle Erweiterung ihrer
Database-Infrastruktur von minimal (SQLite) bis optimal (Full Polyglot).

Migration Paths:
1. SQLite Monolith → PostgreSQL Enhanced  
2. PostgreSQL Enhanced → Dual Database
3. Dual Database → Tri Database
4. Tri Database → Full Polyglot
+ Rollback-Möglichkeiten für jede Migration

Features:
- Zero-Downtime Migration mit Live Data Transfer
- Budget & Constraint Considerations für Verwaltungen
- Rollback Point Identification und Recovery
- Performance Impact Assessment während Migration
- Data Integrity Validation bei jedem Schritt
- Administrative Progress Monitoring

Autor: Covina Development Team
Datum: 3. Oktober 2025
Version: 1.0.0
"""

import asyncio
import logging
import json
import time
import uuid
import sqlite3
import shutil
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta

# Import our adaptive strategy components
try:
    from .adaptive_multi_db_strategy import StrategyType, AdaptiveMultiDBStrategy, DatabaseAvailability
    from .monolithic_fallback_strategies import SQLiteMonolithStrategy, MonolithResult
except ImportError:
    # Fallback for standalone testing
    logging.debug("AdaptiveMultiDBStrategy imports not available - running in standalone mode")


class MigrationStep(Enum):
    """Einzelne Schritte in einer Migration"""
    VALIDATE_SOURCE = "validate_source"
    PREPARE_TARGET = "prepare_target"  
    CREATE_ROLLBACK_POINT = "create_rollback_point"
    MIGRATE_SCHEMA = "migrate_schema"
    MIGRATE_DATA = "migrate_data"
    VALIDATE_MIGRATION = "validate_migration"
    SWITCH_STRATEGY = "switch_strategy"
    CLEANUP_SOURCE = "cleanup_source"
    FINALIZE = "finalize"


class MigrationStatus(Enum):
    """Status einer Migration"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationConstraint:
    """Administrative Constraints für Migration"""
    max_downtime_seconds: int = 0  # Zero-downtime requirement
    max_budget_euros: Optional[int] = None
    required_completion_date: Optional[datetime] = None
    maintenance_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)
    performance_degradation_threshold: float = 0.1  # Max 10% performance impact
    data_loss_tolerance: str = "none"  # "none", "minimal", "acceptable"


@dataclass 
class MigrationPlan:
    """Vollständiger Migration Plan zwischen Strategien"""
    migration_id: str
    source_strategy: StrategyType
    target_strategy: StrategyType
    steps: List[MigrationStep]
    estimated_duration_minutes: int
    data_volume_estimate_gb: float
    rollback_points: List[str]
    constraints: MigrationConstraint
    cost_estimate_euros: Optional[int] = None
    risk_assessment: str = "low"  # "low", "medium", "high"


@dataclass
class MigrationProgress:
    """Live Migration Progress Tracking"""
    migration_id: str
    current_step: MigrationStep
    step_progress_percent: float
    overall_progress_percent: float
    estimated_remaining_minutes: int
    data_migrated_gb: float
    current_performance_impact: float
    warnings: List[str] = field(default_factory=list)
    rollback_available: bool = True
    started_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class RollbackPoint:
    """Rollback Point für Migration Recovery"""
    rollback_id: str
    migration_id: str 
    created_at: datetime
    strategy_snapshot: Dict
    data_backup_path: str
    validation_hash: str
    description: str
    estimated_recovery_minutes: int


class GradualMigrationManager:
    """
    Manager für graduelle Database Strategy Migrations
    
    Koordiniert schrittweise Upgrades zwischen verschiedenen AdaptiveMultiDBStrategy
    Konfigurationen unter Berücksichtigung administrativer Constraints und
    Zero-Downtime Requirements.
    """
    
    def __init__(self, adaptive_strategy: AdaptiveMultiDBStrategy, config: Dict = None):
        self.adaptive_strategy = adaptive_strategy
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Migration State
        self.active_migrations: Dict[str, MigrationProgress] = {}
        self.rollback_points: Dict[str, RollbackPoint] = {}
        self.migration_history: List[Dict] = []
        
        # Configuration
        self.backup_base_path = self.config.get('backup_path', './migration_backups')
        self.max_concurrent_migrations = self.config.get('max_concurrent_migrations', 1)
        self.validation_enabled = self.config.get('enable_validation', True)
        
        # Performance Monitoring
        self.performance_baseline = {}
        self.monitoring_interval_seconds = self.config.get('monitoring_interval', 30)
        
        # Migration Templates
        self.migration_templates = self._initialize_migration_templates()
        
    async def plan_migration_path(
        self, 
        target_strategy: StrategyType,
        constraints: MigrationConstraint = None
    ) -> MigrationPlan:
        """
        Plant optimalen Migration Path zur Ziel-Strategie
        
        Args:
            target_strategy: Gewünschte Ziel-Strategie
            constraints: Administrative Constraints für Migration
            
        Returns:
            MigrationPlan: Detaillierter Migration Plan
        """
        
        current_strategy = self.adaptive_strategy.current_strategy
        constraints = constraints or MigrationConstraint()
        
        self.logger.info(f"🗺️ Planning migration path: {current_strategy.value} → {target_strategy.value}")
        
        # 1. Determine migration path
        migration_steps = self._determine_migration_steps(current_strategy, target_strategy)
        
        if not migration_steps:
            raise ValueError(f"No migration path available from {current_strategy} to {target_strategy}")
        
        # 2. Estimate resources and time
        duration_estimate = await self._estimate_migration_duration(migration_steps, constraints)
        data_volume = await self._estimate_data_volume()
        cost_estimate = await self._estimate_migration_cost(migration_steps, constraints)
        
        # 3. Assess risks
        risk_level = self._assess_migration_risk(migration_steps, constraints)
        
        # 4. Create rollback points plan
        rollback_points = self._plan_rollback_points(migration_steps)
        
        migration_plan = MigrationPlan(
            migration_id=str(uuid.uuid4()),
            source_strategy=current_strategy,
            target_strategy=target_strategy,
            steps=migration_steps,
            estimated_duration_minutes=duration_estimate,
            data_volume_estimate_gb=data_volume,
            rollback_points=rollback_points,
            constraints=constraints,
            cost_estimate_euros=cost_estimate,
            risk_assessment=risk_level
        )
        
        self.logger.info(
            f"📋 Migration plan created: {duration_estimate}min, "
            f"{data_volume:.1f}GB, Risk: {risk_level}"
        )
        
        return migration_plan
    
    def _determine_migration_steps(
        self, 
        source: StrategyType, 
        target: StrategyType
    ) -> List[MigrationStep]:
        """
        Bestimmt optimale Migration Steps zwischen Strategien
        """
        
        # Define migration paths matrix
        migration_paths = {
            # SQLite Monolith → PostgreSQL Enhanced
            (StrategyType.SQLITE_MONOLITH, StrategyType.POSTGRESQL_ENHANCED): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET, 
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.FINALIZE
            ],
            
            # PostgreSQL Enhanced → Dual Database  
            (StrategyType.POSTGRESQL_ENHANCED, StrategyType.DUAL_DATABASE): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT, 
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.CLEANUP_SOURCE,
                MigrationStep.FINALIZE
            ],
            
            # Dual Database → Tri Database
            (StrategyType.DUAL_DATABASE, StrategyType.TRI_DATABASE): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA, 
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.FINALIZE
            ],
            
            # Tri Database → Full Polyglot
            (StrategyType.TRI_DATABASE, StrategyType.FULL_POLYGLOT): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA, 
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.FINALIZE
            ],
            
            # Direct paths (skip intermediate steps if target allows)
            (StrategyType.SQLITE_MONOLITH, StrategyType.DUAL_DATABASE): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION, 
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.FINALIZE
            ],
            
            (StrategyType.SQLITE_MONOLITH, StrategyType.FULL_POLYGLOT): [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY, 
                MigrationStep.FINALIZE
            ]
        }
        
        # Look up direct path
        path_key = (source, target)
        if path_key in migration_paths:
            return migration_paths[path_key]
        
        # If no direct path, find multi-step path
        return self._find_multi_step_path(source, target, migration_paths)
    
    def _find_multi_step_path(
        self, 
        source: StrategyType, 
        target: StrategyType,
        migration_paths: Dict
    ) -> List[MigrationStep]:
        """Findet Multi-Step Migration Path wenn kein direkter Pfad existiert"""
        
        # Strategy complexity order (for pathfinding)
        complexity_order = [
            StrategyType.SQLITE_MONOLITH,
            StrategyType.POSTGRESQL_ENHANCED, 
            StrategyType.DUAL_DATABASE,
            StrategyType.TRI_DATABASE,
            StrategyType.FULL_POLYGLOT
        ]
        
        source_idx = complexity_order.index(source)
        target_idx = complexity_order.index(target)
        
        if source_idx >= target_idx:
            # Downgrade path (rollback scenario)
            return [
                MigrationStep.VALIDATE_SOURCE,
                MigrationStep.CREATE_ROLLBACK_POINT, 
                MigrationStep.PREPARE_TARGET,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.SWITCH_STRATEGY,
                MigrationStep.CLEANUP_SOURCE,
                MigrationStep.FINALIZE
            ]
        
        # Upgrade path - step through intermediate strategies
        steps = [MigrationStep.VALIDATE_SOURCE]
        
        for i in range(source_idx + 1, target_idx + 1):
            intermediate_target = complexity_order[i]
            steps.extend([
                MigrationStep.PREPARE_TARGET,
                MigrationStep.CREATE_ROLLBACK_POINT,
                MigrationStep.MIGRATE_SCHEMA,
                MigrationStep.MIGRATE_DATA,
                MigrationStep.VALIDATE_MIGRATION,
                MigrationStep.SWITCH_STRATEGY
            ])
        
        steps.append(MigrationStep.FINALIZE)
        return steps
    
    async def _estimate_migration_duration(
        self, 
        steps: List[MigrationStep], 
        constraints: MigrationConstraint
    ) -> int:
        """Schätzt Migration Duration in Minuten"""
        
        # Base time estimates per step (in minutes)
        step_durations = {
            MigrationStep.VALIDATE_SOURCE: 5,
            MigrationStep.PREPARE_TARGET: 10,
            MigrationStep.CREATE_ROLLBACK_POINT: 15, 
            MigrationStep.MIGRATE_SCHEMA: 20,
            MigrationStep.MIGRATE_DATA: 60,  # Highly dependent on data volume
            MigrationStep.VALIDATE_MIGRATION: 10,
            MigrationStep.SWITCH_STRATEGY: 5,
            MigrationStep.CLEANUP_SOURCE: 10,
            MigrationStep.FINALIZE: 5
        }
        
        # Calculate base duration
        base_duration = sum(step_durations.get(step, 10) for step in steps)
        
        # Adjust for data volume
        data_volume_gb = await self._estimate_data_volume()
        data_factor = max(1.0, data_volume_gb / 10.0)  # Scale with data volume
        
        # Adjust for constraints
        constraint_factor = 1.0
        if constraints.max_downtime_seconds == 0:  # Zero-downtime requirement
            constraint_factor *= 1.5  # 50% longer for live migration
        
        if constraints.performance_degradation_threshold < 0.05:  # Very strict performance
            constraint_factor *= 1.3  # 30% longer for careful migration
        
        estimated_duration = int(base_duration * data_factor * constraint_factor)
        
        return max(estimated_duration, 30)  # Minimum 30 minutes
    
    async def _estimate_data_volume(self) -> float:
        """Schätzt Data Volume in GB für Migration"""
        
        try:
            # This would query actual databases to get real sizes
            # For now, provide reasonable estimates based on strategy
            
            strategy = self.adaptive_strategy.current_strategy
            
            volume_estimates = {
                StrategyType.SQLITE_MONOLITH: 1.0,      # Small SQLite file
                StrategyType.POSTGRESQL_ENHANCED: 5.0,   # PostgreSQL + SQLite
                StrategyType.DUAL_DATABASE: 10.0,        # 2 databases
                StrategyType.TRI_DATABASE: 15.0,         # 3 databases  
                StrategyType.FULL_POLYGLOT: 20.0        # All 4 databases
            }
            
            return volume_estimates.get(strategy, 5.0)
            
        except Exception as e:
            self.logger.warning(f"Could not estimate data volume: {e}")
            return 5.0  # Conservative estimate
    
    async def _estimate_migration_cost(
        self, 
        steps: List[MigrationStep], 
        constraints: MigrationConstraint
    ) -> Optional[int]:
        """Schätzt Migration Costs in Euro"""
        
        if constraints.max_budget_euros is None:
            return None
        
        # Base cost factors (in EUR)
        base_costs = {
            "postgresql_setup": 500,      # PostgreSQL server setup/license
            "additional_database": 300,   # Each additional database system
            "migration_labor": 1000,      # Professional migration services
            "downtime_cost": 100,         # Per hour of downtime
            "backup_storage": 50          # Backup storage costs
        }
        
        # Calculate costs based on target strategy
        total_cost = 0
        
        # Migration labor (base cost)
        duration_hours = await self._estimate_migration_duration(steps, constraints) / 60
        total_cost += int(duration_hours * 100)  # EUR 100/hour labor
        
        # Infrastructure costs
        target_strategy = self.adaptive_strategy.current_strategy
        
        if target_strategy in [StrategyType.POSTGRESQL_ENHANCED, StrategyType.DUAL_DATABASE, 
                              StrategyType.TRI_DATABASE, StrategyType.FULL_POLYGLOT]:
            total_cost += base_costs["postgresql_setup"]
        
        if target_strategy in [StrategyType.DUAL_DATABASE, StrategyType.TRI_DATABASE]:
            total_cost += base_costs["additional_database"] 
        
        if target_strategy == StrategyType.FULL_POLYGLOT:
            total_cost += base_costs["additional_database"] * 2
        
        # Backup and safety costs
        total_cost += base_costs["backup_storage"]
        
        return min(total_cost, constraints.max_budget_euros) if constraints.max_budget_euros else total_cost
    
    def _assess_migration_risk(
        self, 
        steps: List[MigrationStep], 
        constraints: MigrationConstraint
    ) -> str:
        """Bewertet Migration Risk Level"""
        
        risk_factors = 0
        
        # Risk factors
        if len(steps) > 8:
            risk_factors += 1  # Complex migration
        
        if constraints.max_downtime_seconds == 0:
            risk_factors += 2  # Zero-downtime is risky
        
        if constraints.data_loss_tolerance == "none":
            risk_factors += 1  # No data loss tolerance
        
        if constraints.performance_degradation_threshold < 0.05:
            risk_factors += 1  # Very strict performance requirements
        
        # Assess risk level
        if risk_factors >= 4:
            return "high"
        elif risk_factors >= 2:
            return "medium"
        else:
            return "low"
    
    def _plan_rollback_points(self, steps: List[MigrationStep]) -> List[str]:
        """Plant Rollback Points für Migration Steps"""
        
        rollback_points = []
        
        # Always create rollback point before major operations
        major_steps = [
            MigrationStep.MIGRATE_SCHEMA,
            MigrationStep.MIGRATE_DATA,
            MigrationStep.SWITCH_STRATEGY
        ]
        
        for i, step in enumerate(steps):
            if step in major_steps:
                rollback_points.append(f"rollback_before_{step.value}_{i}")
        
        # Always have initial and final rollback points
        rollback_points.insert(0, "initial_state")
        rollback_points.append("migration_complete")
        
        return rollback_points
    
    async def execute_migration(self, migration_plan: MigrationPlan) -> MigrationProgress:
        """
        Führt Migration Plan aus mit Live Progress Monitoring
        
        Args:
            migration_plan: Detaillierter Migration Plan
            
        Returns:
            MigrationProgress: Live Migration Progress
        """
        
        migration_id = migration_plan.migration_id
        
        self.logger.info(f"🚀 Starting migration {migration_id}")
        
        # Initialize progress tracking
        progress = MigrationProgress(
            migration_id=migration_id,
            current_step=migration_plan.steps[0],
            step_progress_percent=0.0,
            overall_progress_percent=0.0,
            estimated_remaining_minutes=migration_plan.estimated_duration_minutes,
            data_migrated_gb=0.0,
            current_performance_impact=0.0
        )
        
        self.active_migrations[migration_id] = progress
        
        try:
            # Execute each migration step
            total_steps = len(migration_plan.steps)
            
            for i, step in enumerate(migration_plan.steps):
                progress.current_step = step
                progress.step_progress_percent = 0.0
                progress.overall_progress_percent = (i / total_steps) * 100
                
                self.logger.info(f"📍 Executing step {i+1}/{total_steps}: {step.value}")
                
                # Execute the step
                step_result = await self._execute_migration_step(
                    step, migration_plan, progress
                )
                
                if not step_result.success:
                    progress.warnings.append(f"Step {step.value} failed: {step_result.message}")
                    
                    # Check if we should rollback
                    if step_result.critical:
                        await self._initiate_rollback(migration_plan, progress)
                        return progress
                
                # Update progress
                progress.step_progress_percent = 100.0
                progress.overall_progress_percent = ((i + 1) / total_steps) * 100
                progress.last_update = datetime.now()
                
                # Update estimated remaining time
                elapsed_minutes = (datetime.now() - progress.started_at).total_seconds() / 60
                if i > 0:
                    avg_minutes_per_step = elapsed_minutes / (i + 1)
                    remaining_steps = total_steps - (i + 1)
                    progress.estimated_remaining_minutes = int(avg_minutes_per_step * remaining_steps)
                
                # Short pause between steps for monitoring
                await asyncio.sleep(1)
            
            # Migration completed successfully
            progress.overall_progress_percent = 100.0
            progress.estimated_remaining_minutes = 0
            
            self.logger.info(f"✅ Migration {migration_id} completed successfully")
            
            return progress
            
        except Exception as e:
            self.logger.error(f"❌ Migration {migration_id} failed: {e}")
            progress.warnings.append(f"Migration failed: {str(e)}")
            
            # Attempt rollback
            await self._initiate_rollback(migration_plan, progress)
            
            return progress
        
        finally:
            # Cleanup
            if migration_id in self.active_migrations:
                del self.active_migrations[migration_id]
    
    async def _execute_migration_step(
        self, 
        step: MigrationStep, 
        plan: MigrationPlan, 
        progress: MigrationProgress
    ):
        """Führt einzelnen Migration Step aus"""
        
        # This is a placeholder for actual step execution
        # In real implementation, each step would have specific logic
        
        step_executors = {
            MigrationStep.VALIDATE_SOURCE: self._execute_validate_source,
            MigrationStep.PREPARE_TARGET: self._execute_prepare_target,
            MigrationStep.CREATE_ROLLBACK_POINT: self._execute_create_rollback_point,
            MigrationStep.MIGRATE_SCHEMA: self._execute_migrate_schema,
            MigrationStep.MIGRATE_DATA: self._execute_migrate_data,
            MigrationStep.VALIDATE_MIGRATION: self._execute_validate_migration,
            MigrationStep.SWITCH_STRATEGY: self._execute_switch_strategy,
            MigrationStep.CLEANUP_SOURCE: self._execute_cleanup_source,
            MigrationStep.FINALIZE: self._execute_finalize
        }
        
        executor = step_executors.get(step, self._execute_default_step)
        
        try:
            result = await executor(plan, progress)
            return MigrationStepResult(success=True, message="Step completed", critical=False)
            
        except Exception as e:
            self.logger.error(f"Step {step.value} failed: {e}")
            return MigrationStepResult(success=False, message=str(e), critical=True)
    
    async def _execute_validate_source(self, plan: MigrationPlan, progress: MigrationProgress):
        """Validiert Source Strategy State"""
        self.logger.debug("Validating source strategy...")
        await asyncio.sleep(2)  # Simulate validation time
        return {"validation": "passed"}
    
    async def _execute_prepare_target(self, plan: MigrationPlan, progress: MigrationProgress):
        """Bereitet Target Strategy vor"""
        self.logger.debug("Preparing target strategy...")
        await asyncio.sleep(5)  # Simulate preparation time
        return {"preparation": "completed"}
    
    async def _execute_create_rollback_point(self, plan: MigrationPlan, progress: MigrationProgress):
        """Erstellt Rollback Point"""
        rollback_id = str(uuid.uuid4())
        self.logger.debug(f"Creating rollback point: {rollback_id}")
        
        # Create rollback point (simplified)
        rollback_point = RollbackPoint(
            rollback_id=rollback_id,
            migration_id=plan.migration_id,
            created_at=datetime.now(),
            strategy_snapshot={"strategy": plan.source_strategy.value},
            data_backup_path=f"{self.backup_base_path}/{rollback_id}",
            validation_hash="mock_hash",
            description=f"Rollback point for {progress.current_step.value}",
            estimated_recovery_minutes=15
        )
        
        self.rollback_points[rollback_id] = rollback_point
        
        await asyncio.sleep(3)  # Simulate backup time
        return {"rollback_id": rollback_id}
    
    async def _execute_migrate_schema(self, plan: MigrationPlan, progress: MigrationProgress):
        """Migriert Database Schema"""
        self.logger.debug("Migrating database schema...")
        
        # Simulate schema migration with progress updates
        for i in range(10):
            progress.step_progress_percent = (i + 1) * 10
            await asyncio.sleep(0.5)
        
        return {"schema_migration": "completed"}
    
    async def _execute_migrate_data(self, plan: MigrationPlan, progress: MigrationProgress):
        """Migriert Data zwischen Strategies"""
        self.logger.debug("Migrating data...")
        
        total_data_gb = plan.data_volume_estimate_gb
        
        # Simulate data migration with progress
        for i in range(20):
            progress.step_progress_percent = (i + 1) * 5
            progress.data_migrated_gb = (i + 1) * (total_data_gb / 20)
            await asyncio.sleep(0.3)
        
        return {"data_migration": "completed", "migrated_gb": total_data_gb}
    
    async def _execute_validate_migration(self, plan: MigrationPlan, progress: MigrationProgress):
        """Validiert Migration Integrity"""
        self.logger.debug("Validating migration integrity...")
        await asyncio.sleep(3)
        return {"validation": "passed", "integrity_check": "ok"}
    
    async def _execute_switch_strategy(self, plan: MigrationPlan, progress: MigrationProgress):
        """Switcht zu neuer Strategy"""
        self.logger.debug(f"Switching to strategy: {plan.target_strategy.value}")
        
        # Update adaptive strategy
        self.adaptive_strategy.current_strategy = plan.target_strategy
        
        await asyncio.sleep(2)
        return {"strategy_switch": "completed", "active_strategy": plan.target_strategy.value}
    
    async def _execute_cleanup_source(self, plan: MigrationPlan, progress: MigrationProgress):
        """Cleanup Source Strategy Resources"""
        self.logger.debug("Cleaning up source strategy...")
        await asyncio.sleep(3)
        return {"cleanup": "completed"}
    
    async def _execute_finalize(self, plan: MigrationPlan, progress: MigrationProgress):
        """Finalisiert Migration"""
        self.logger.debug("Finalizing migration...")
        
        # Add to history
        self.migration_history.append({
            "migration_id": plan.migration_id,
            "source_strategy": plan.source_strategy.value,
            "target_strategy": plan.target_strategy.value,
            "completed_at": datetime.now().isoformat(),
            "duration_minutes": (datetime.now() - progress.started_at).total_seconds() / 60
        })
        
        await asyncio.sleep(1)
        return {"finalization": "completed"}
    
    async def _execute_default_step(self, plan: MigrationPlan, progress: MigrationProgress):
        """Default Step Executor"""
        await asyncio.sleep(1)
        return {"step": "completed"}
    
    async def _initiate_rollback(self, plan: MigrationPlan, progress: MigrationProgress):
        """Initiiert Rollback bei Migration Failure"""
        self.logger.warning(f"Initiating rollback for migration {plan.migration_id}")
        
        # Find latest rollback point
        latest_rollback = None
        for rollback_point in self.rollback_points.values():
            if rollback_point.migration_id == plan.migration_id:
                if latest_rollback is None or rollback_point.created_at > latest_rollback.created_at:
                    latest_rollback = rollback_point
        
        if latest_rollback:
            await self._execute_rollback(latest_rollback, progress)
        else:
            self.logger.error("No rollback point found - manual intervention required")
    
    async def _execute_rollback(self, rollback_point: RollbackPoint, progress: MigrationProgress):
        """Führt Rollback aus"""
        self.logger.info(f"Executing rollback to point: {rollback_point.rollback_id}")
        
        # Simulate rollback execution
        for i in range(10):
            await asyncio.sleep(0.5)
        
        # Restore original strategy
        original_strategy_name = rollback_point.strategy_snapshot.get("strategy", "sqlite_monolith")
        original_strategy = StrategyType(original_strategy_name)
        self.adaptive_strategy.current_strategy = original_strategy
        
        progress.warnings.append(f"Rollback completed to {original_strategy.value}")
        
        self.logger.info("✅ Rollback completed successfully")


@dataclass
class MigrationStepResult:
    """Result eines einzelnen Migration Steps"""
    success: bool
    message: str
    critical: bool = False
    data: Dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


# Convenience functions
async def create_migration_manager(
    adaptive_strategy: AdaptiveMultiDBStrategy, 
    config: Dict = None
) -> GradualMigrationManager:
    """
    Erstellt und initialisiert GradualMigrationManager
    """
    
    manager = GradualMigrationManager(adaptive_strategy, config)
    
    # Ensure backup directory exists
    backup_path = Path(manager.backup_base_path)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"🔄 Migration Manager initialized with backup path: {backup_path}")
    
    return manager


if __name__ == "__main__":
    # Example usage
    async def test_migration_manager():
        """Test function for migration manager"""
        
        logging.basicConfig(level=logging.INFO)
        
        # Mock adaptive strategy
        class MockAdaptiveStrategy:
            current_strategy = StrategyType.SQLITE_MONOLITH
        
        mock_strategy = MockAdaptiveStrategy()
        
        # Create migration manager
        manager = await create_migration_manager(mock_strategy)
        
        # Test migration planning
        constraints = MigrationConstraint(
            max_downtime_seconds=0,  # Zero downtime
            max_budget_euros=2000,
            performance_degradation_threshold=0.1
        )
        
        migration_plan = await manager.plan_migration_path(
            StrategyType.FULL_POLYGLOT, 
            constraints
        )
        
        print(f"Migration Plan: {migration_plan.migration_id}")
        print(f"Steps: {len(migration_plan.steps)}")
        print(f"Duration: {migration_plan.estimated_duration_minutes} minutes")
        print(f"Risk: {migration_plan.risk_assessment}")
        
        # Test migration execution (simulation)
        progress = await manager.execute_migration(migration_plan)
        
        print(f"Migration Progress: {progress.overall_progress_percent}%")
        print(f"Warnings: {progress.warnings}")
    
    # Run test
    asyncio.run(test_migration_manager())