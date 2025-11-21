# NodeNext Module Resolution Guide for TSX Files

## Overview

This guide documents the solution for TypeScript compilation issues with TSX files when using NodeNext module resolution, specifically addressing the error:

```
Module './MetricsChart.js' was resolved to '.../MetricsChart.tsx', but '--jsx' is not set.
Relative import paths need explicit file extensions in ECMAScript imports when '--moduleResolution' is 'node16' or 'nodenext'.
```

## Problem Analysis

The issue occurred because:

1. **Main project** uses `"module": "NodeNext"` and `"moduleResolution": "NodeNext"` which requires explicit file extensions in imports
2. **TSX files** in `src/web/ui/analytics/` were being compiled with the main project's configuration
3. **Missing JSX configuration** - the main tsconfig.json lacked `"jsx": "react-jsx"`
4. **Module resolution conflict** - NodeNext requires `.js` extensions, but UI components are TypeScript files

## Solution Implemented

### 1. Added JSX Support to Main Configuration

Updated `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/tsconfig.json`:

```json
{
  "compilerOptions": {
    // ... existing options ...
    "jsx": "react-jsx",
    "allowJs": true
  },
  "include": ["src/**/*", "**/*.test.ts", "**/*.spec.ts", "vitest.config.ts"],
  "exclude": ["node_modules", "src/web/ui"]
}
```

### 2. Created Separate Configuration for Web UI Analytics

Created `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/src/web/ui/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "esnext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "downlevelIteration": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["../../../app/ui/src/*"],
      "@core/*": ["../../../core/*"]
    },
    "strict": false,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "types": ["node"],
    "lib": ["ES2022", "DOM"],
    "declaration": true,
    "declarationMap": true,
    "jsx": "react-jsx",
    "allowJs": true,
    "noEmit": false
  },
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
```

### 3. Fixed Cross-Platform Build Script

Updated `package.json` to use Node.js for cross-platform file operations:

```json
{
  "scripts": {
    "clean": "node -e \"require('fs').rmSync('dist', { recursive: true, force: true })\""
  }
}
```

## Key Differences Between Configurations

### Main Project (NodeNext)
- `"module": "NodeNext"`
- `"moduleResolution": "NodeNext"`
- Requires explicit `.js` extensions in imports
- Excludes `src/web/ui` to avoid conflicts

### Web UI Analytics (Bundler)
- `"module": "esnext"`
- `"moduleResolution": "bundler"`
- Allows standard TypeScript imports without extensions
- Uses path mapping for UI components

## Best Practices

### 1. Separate TypeScript Configurations
- Use NodeNext for backend/server code
- Use bundler for frontend/UI components
- Create separate `tsconfig.json` files for different parts of your project

### 2. Import Path Management
- **NodeNext**: Always use explicit file extensions: `import { something } from './module.js'`
- **Bundler**: Use standard TypeScript imports: `import { something } from './module'`

### 3. JSX Configuration
- Always include `"jsx": "react-jsx"` when working with React/TSX files
- Add `"allowJs": true` for mixed JavaScript/TypeScript projects

## Troubleshooting

### Common Issues

1. **"Cannot find module" errors**
   - Check that the module resolution strategy matches your import style
   - Verify path mappings in tsconfig.json

2. **"JSX element implicitly has type 'any'" errors**
   - Ensure `"jsx": "react-jsx"` is set in your tsconfig.json
   - Install required React type definitions: `@types/react`

3. **"Relative import paths need explicit file extensions"**
   - You're using NodeNext module resolution - add `.js` extensions
   - Or switch to bundler module resolution for UI components

### Migration Steps

1. Identify which parts of your project need NodeNext vs bundler
2. Create separate TypeScript configurations
3. Update import paths accordingly
4. Test compilation with `tsc --noEmit`
5. Update build scripts for cross-platform compatibility

## Verification

The solution has been verified to:
- ✅ Fix the original JSX configuration error
- ✅ Allow TSX files to compile without NodeNext extension requirements
- ✅ Maintain proper module resolution for both backend and frontend code
- ✅ Support cross-platform development (Windows/Linux/macOS)

## Related Files

- `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/tsconfig.json` - Main project configuration
- `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/src/web/ui/tsconfig.json` - Web UI analytics configuration
- `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/src/app/ui/tsconfig.json` - UI project configuration
- `pmoves_multi_agent_pro_pack/memory_shim/pmoves_cipher/package.json` - Build scripts and dependencies