# PMOVES Agent Packs Migration Plan

## Overview

This document outlines the phased migration strategy to consolidate the four separate PMOVES agent packs into a single unified repository structure. The migration maintains backward compatibility while enabling a smooth transition to the new architecture.

## Current State Analysis

### Existing Agent Packs
1. **`pmoves_multi_agent_pack/`** - Basic multi-agent setup with Docling and Postman
2. **`pmoves_multi_agent_pro_pack/`** - Adds E2B and VL Sentinel
3. **`pmoves_multi_agent_pro_plus_pack/`** - Adds local Postman MCP
4. **`pmoves-mini-agent-box/`** - Lightweight mini agent with Discord/Slack integration

### Key Differences
- **Structure**: Each pack has its own complete setup (Docker Compose, env files, modes)
- **Duplication**: ~70% code duplication across packs
- **Maintenance**: Updates require changes in multiple locations
- **Onboarding**: New users must choose one pack, limiting feature combinations

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1-2)
**Goal**: Establish unified core without breaking existing setups

#### Tasks:
1. **Create unified directory structure**
   - Move shared components to `core/` directory
   - Create `features/` directory for pack-specific modules
   - Establish `config/` and `scripts/` directories

2. **Migrate shared components**
   - Consolidate kilocode modes to `core/mcp/modes/`
   - Create base Docker Compose in `core/docker-compose/base.yml`
   - Standardize environment variables in `core/example.env`

3. **Implement feature flags system**
   - Create `config/feature-flags.md` documentation
   - Develop setup scripts with configuration options
   - Test feature flag combinations

#### Compatibility:
- ✅ Existing pack directories remain functional
- ✅ No breaking changes to current deployments
- ✅ New unified setup available alongside legacy packs

### Phase 2: Feature Module Migration (Week 3-4)
**Goal**: Migrate pack-specific features to modular structure

#### Tasks:
1. **Pro features migration**
   - Move E2B shim to `features/pro/e2b_shim/`
   - Move VL sentinel to `features/pro/vl_sentinel/`
   - Create `features/pro/docker-compose.yml`

2. **Mini features migration**
   - Move Crush shim to `features/mini/crush_shim/`
   - Move Discord bot to `features/mini/discord_bot/`
   - Create `features/mini/docker-compose.yml`

3. **Pro-plus features migration**
   - Create `features/pro-plus/docker-compose.yml` for local Postman
   - Update environment configurations

#### Compatibility:
- ✅ Legacy packs continue working
- ✅ New modular features available
- ✅ Cross-pack feature combinations now possible

### Phase 3: Documentation and Testing (Week 5-6)
**Goal**: Complete documentation and validation

#### Tasks:
1. **Create comprehensive documentation**
   - Setup guide (`docs/SETUP_GUIDE.md`)
   - Migration guide (this document)
   - Feature matrix and compatibility chart

2. **Develop migration tools**
   - Automated migration script for existing deployments
   - Configuration converter for legacy `.env` files
   - Validation scripts for setup integrity

3. **Testing and validation**
   - Test all feature combinations
   - Validate backward compatibility
   - Performance testing across configurations

#### Compatibility:
- ✅ Full backward compatibility maintained
- ✅ Migration tools available
- ✅ Comprehensive documentation provided

### Phase 4: Deprecation and Cleanup (Week 7-8)
**Goal**: Transition to unified structure

#### Tasks:
1. **Mark legacy packs as deprecated**
   - Add deprecation notices to legacy directories
   - Update documentation to reference unified setup
   - Provide migration incentives

2. **Gradual cleanup**
   - Remove legacy pack directories (6 months after deprecation)
   - Update all references in documentation
   - Archive legacy code for reference

#### Compatibility:
- ⚠️ Legacy packs marked as deprecated but functional
- ✅ Unified structure as primary setup method
- ✅ Migration support available

## Migration Timeline

```
Week 1-2: Core Infrastructure
├── Create unified directory structure
├── Migrate shared components
└── Implement feature flags

Week 3-4: Feature Module Migration
├── Pro features migration
├── Mini features migration
└── Pro-plus features migration

Week 5-6: Documentation and Testing
├── Create comprehensive docs
├── Develop migration tools
└── Testing and validation

Week 7-8: Deprecation and Cleanup
├── Mark legacy packs deprecated
└── Gradual cleanup
```

## User Migration Paths

### For Existing Users

#### Option 1: Gradual Migration (Recommended)
1. **Continue using current setup** - No immediate action required
2. **Test unified setup** - Deploy alongside existing setup
3. **Migrate when ready** - Use migration tools to convert configuration
4. **Decommission legacy** - Remove old setup after validation

#### Option 2: Immediate Migration
1. **Backup current configuration** - Save `.env` and customizations
2. **Run migration script** - Automated conversion to unified structure
3. **Test new deployment** - Validate all features work correctly
4. **Switch over** - Update production deployment

### For New Users
- Use unified setup from the start
- Select appropriate feature combination via setup script
- Benefit from simplified maintenance and feature flexibility

## Risk Mitigation

### Technical Risks
- **Breaking changes**: Comprehensive testing of all feature combinations
- **Performance impact**: Benchmarking before and after migration
- **Compatibility issues**: Maintain legacy support during transition

### Operational Risks
- **User confusion**: Clear documentation and migration guides
- **Support burden**: Phased rollout with support for both systems
- **Data loss**: Backup procedures and validation scripts

## Success Metrics

### Technical Metrics
- ✅ All feature combinations tested and functional
- ✅ Zero breaking changes during transition period
- ✅ Performance maintained or improved
- ✅ Code duplication reduced by >70%

### User Experience Metrics
- ✅ Clear migration path for existing users
- ✅ Simplified setup for new users
- ✅ Comprehensive documentation available
- ✅ Support for legacy setups during transition

## Rollback Plan

If issues arise during migration:

1. **Immediate rollback**: Legacy packs remain functional
2. **Issue isolation**: Identify and fix problems in unified structure
3. **Staged redeployment**: Test fixes before full rollout
4. **Communication**: Inform users of any temporary issues

## Support and Communication

### During Migration
- **Documentation**: Comprehensive guides for all migration paths
- **Support channels**: Dedicated support for migration issues
- **Community**: Forums and discussions for user questions

### Post-Migration
- **Unified documentation**: Single source of truth
- **Feature requests**: Centralized issue tracking
- **Updates**: Simplified release process for all configurations

## Conclusion

This migration plan provides a structured approach to consolidating the PMOVES agent packs into a unified, maintainable architecture. The phased approach ensures minimal disruption while delivering significant improvements in code organization, feature flexibility, and user experience.

The unified structure enables:
- **70% reduction** in code duplication
- **Flexible feature combinations** instead of rigid pack choices
- **Simplified maintenance** with centralized updates
- **Better user experience** with clear setup paths
- **Future extensibility** for new agent types and features