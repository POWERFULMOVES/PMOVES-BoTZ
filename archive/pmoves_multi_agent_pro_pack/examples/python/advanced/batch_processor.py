#!/usr/bin/env python3
"""
Docling MCP Python Client - Advanced Batch Processing Example

This example demonstrates advanced batch processing capabilities including:
- Concurrent document processing
- Progress tracking
- Error handling and recovery
- Performance optimization
- Result aggregation and reporting
"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import statistics


class ProcessingStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingResult:
    """Result of document processing."""
    file_path: str
    status: ProcessingStatus
    output: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    file_size: int = 0
    output_format: str = "markdown"


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing."""
    max_concurrent: int = 5
    chunk_size: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    enable_progress_callback: bool = True
    continue_on_error: bool = True
    validate_files: bool = True
    supported_formats: List[str] = field(default_factory=lambda: [
        ".pdf", ".docx", ".pptx", ".xlsx", ".html", ".txt", ".md"
    ])


class BatchProcessor:
    """Advanced batch document processor with comprehensive features."""
    
    def __init__(self, mcp_client, config: BatchProcessingConfig = None):
        self.client = mcp_client
        self.config = config or BatchProcessingConfig()
        self.logger = logging.getLogger(__name__)
        self.progress_callback: Optional[Callable] = None
        self.results: List[ProcessingResult] = []
        self.start_time: float = 0
        self.total_files: int = 0
        self.processed_files: int = 0
        self.failed_files: int = 0
        self.skipped_files: int = 0
        
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function."""
        self.progress_callback = callback
    
    async def process_batch(
        self, 
        file_paths: List[str], 
        output_format: str = "markdown",
        progress_callback: Optional[Callable] = None
    ) -> List[ProcessingResult]:
        """
        Process a batch of documents with advanced features.
        
        Args:
            file_paths: List of file paths to process
            output_format: Desired output format
            progress_callback: Optional progress callback function
            
        Returns:
            List of ProcessingResult objects
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)
            
        self.start_time = time.time()
        self.total_files = len(file_paths)
        self.processed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.results = []
        
        self.logger.info(f"Starting batch processing of {self.total_files} files")
        
        # Validate files if enabled
        if self.config.validate_files:
            file_paths = await self._validate_files(file_paths)
            self.total_files = len(file_paths)
        
        # Process files in chunks
        chunks = self._create_chunks(file_paths, self.config.chunk_size)
        
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} files)")
            
            # Process chunk concurrently
            chunk_results = await self._process_chunk(
                chunk, output_format, i * self.config.chunk_size
            )
            
            self.results.extend(chunk_results)
            
            # Update progress
            await self._update_progress()
        
        # Generate summary report
        await self._generate_report()
        
        return self.results
    
    async def _validate_files(self, file_paths: List[str]) -> List[str]:
        """Validate and filter files before processing."""
        valid_files = []
        
        for file_path in file_paths:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                self.logger.warning(f"File not found: {file_path}")
                result = ProcessingResult(
                    file_path=file_path,
                    status=ProcessingStatus.SKIPPED,
                    error="File not found"
                )
                self.results.append(result)
                self.skipped_files += 1
                continue
            
            # Check if file is readable
            if not path.is_file() or not os.access(file_path, os.R_OK):
                self.logger.warning(f"File not readable: {file_path}")
                result = ProcessingResult(
                    file_path=file_path,
                    status=ProcessingStatus.SKIPPED,
                    error="File not readable"
                )
                self.results.append(result)
                self.skipped_files += 1
                continue
            
            # Check file extension
            if path.suffix.lower() not in self.config.supported_formats:
                self.logger.warning(f"Unsupported file format: {file_path}")
                result = ProcessingResult(
                    file_path=file_path,
                    status=ProcessingStatus.SKIPPED,
                    error=f"Unsupported format: {path.suffix}"
                )
                self.results.append(result)
                self.skipped_files += 1
                continue
            
            # Check file size (max 100MB)
            file_size = path.stat().st_size
            if file_size > 100 * 1024 * 1024:
                self.logger.warning(f"File too large: {file_path}")
                result = ProcessingResult(
                    file_path=file_path,
                    status=ProcessingStatus.SKIPPED,
                    error="File too large (>100MB)"
                )
                self.results.append(result)
                self.skipped_files += 1
                continue
            
            valid_files.append(file_path)
        
        return valid_files
    
    def _create_chunks(self, items: List[Any], chunk_size: int) -> List[List[Any]]:
        """Create chunks from a list of items."""
        chunks = []
        for i in range(0, len(items), chunk_size):
            chunks.append(items[i:i + chunk_size])
        return chunks
    
    async def _process_chunk(
        self, 
        chunk: List[str], 
        output_format: str, 
        offset: int
    ) -> List[ProcessingResult]:
        """Process a chunk of files concurrently."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        tasks = []
        for i, file_path in enumerate(chunk):
            task = self._process_single_file(
                file_path, output_format, offset + i, semaphore
            )
            tasks.append(task)
        
        # Process all files in the chunk concurrently
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results and exceptions
        results = []
        for result in chunk_results:
            if isinstance(result, Exception):
                # Handle processing exception
                self.logger.error(f"Processing exception: {result}")
                self.failed_files += 1
            else:
                results.append(result)
                if result.status == ProcessingStatus.COMPLETED:
                    self.processed_files += 1
                elif result.status == ProcessingStatus.FAILED:
                    self.failed_files += 1
        
        return results
    
    async def _process_single_file(
        self, 
        file_path: str, 
        output_format: str, 
        index: int, 
        semaphore: asyncio.Semaphore
    ) -> ProcessingResult:
        """Process a single file with retry logic."""
        async with semaphore:
            start_time = time.time()
            
            # Get file info
            file_size = Path(file_path).stat().st_size
            
            self.logger.info(f"Processing file {index + 1}/{self.total_files}: {file_path}")
            
            for attempt in range(1, self.config.retry_attempts + 1):
                try:
                    # Call MCP tool
                    result = await self.client.call_tool(
                        "convert_document",
                        {
                            "file_path": file_path,
                            "output_format": output_format
                        }
                    )
                    
                    processing_time = time.time() - start_time
                    
                    # Extract content from result
                    content = self._extract_content(result)
                    
                    processing_result = ProcessingResult(
                        file_path=file_path,
                        status=ProcessingStatus.COMPLETED,
                        output=content,
                        processing_time=processing_time,
                        file_size=file_size,
                        output_format=output_format
                    )
                    
                    self.logger.info(f"Successfully processed: {file_path} ({processing_time:.2f}s)")
                    return processing_result
                    
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt} failed for {file_path}: {e}")
                    
                    if attempt < self.config.retry_attempts:
                        await asyncio.sleep(self.config.retry_delay * attempt)
                    else:
                        processing_time = time.time() - start_time
                        
                        if self.config.continue_on_error:
                            processing_result = ProcessingResult(
                                file_path=file_path,
                                status=ProcessingStatus.FAILED,
                                error=str(e),
                                processing_time=processing_time,
                                file_size=file_size,
                                output_format=output_format
                            )
                            
                            self.logger.error(f"Failed to process: {file_path} after {attempt} attempts")
                            return processing_result
                        else:
                            raise e
    
    def _extract_content(self, result: Dict[str, Any]) -> str:
        """Extract content from MCP tool result."""
        if isinstance(result, dict) and 'content' in result:
            content = result['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', '')
            elif isinstance(content, str):
                return content
        return str(result)
    
    async def _update_progress(self):
        """Update progress information."""
        if self.progress_callback and self.config.enable_progress_callback:
            progress_data = {
                'total': self.total_files,
                'processed': self.processed_files,
                'failed': self.failed_files,
                'skipped': self.skipped_files,
                'percentage': (self.processed_files + self.failed_files + self.skipped_files) / self.total_files * 100,
                'elapsed_time': time.time() - self.start_time
            }
            
            await self.progress_callback(progress_data)
    
    async def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive processing report."""
        total_time = time.time() - self.start_time
        
        # Calculate statistics
        completed_results = [r for r in self.results if r.status == ProcessingStatus.COMPLETED]
        failed_results = [r for r in self.results if r.status == ProcessingStatus.FAILED]
        
        # Processing time statistics
        processing_times = [r.processing_time for r in completed_results if r.processing_time > 0]
        
        stats = {
            'total_files': self.total_files,
            'completed': len(completed_results),
            'failed': len(failed_results),
            'skipped': self.skipped_files,
            'total_time': total_time,
            'avg_processing_time': statistics.mean(processing_times) if processing_times else 0,
            'min_processing_time': min(processing_times) if processing_times else 0,
            'max_processing_time': max(processing_times) if processing_results else 0,
            'throughput': len(completed_results) / total_time if total_time > 0 else 0
        }
        
        if processing_times:
            stats['p95_processing_time'] = statistics.quantiles(processing_times, n=20)[18]  # 95th percentile
            stats['p99_processing_time'] = statistics.quantiles(processing_times, n=100)[98]  # 99th percentile
        
        # File size statistics
        file_sizes = [r.file_size for r in completed_results if r.file_size > 0]
        if file_sizes:
            stats['total_size'] = sum(file_sizes)
            stats['avg_file_size'] = statistics.mean(file_sizes)
        
        self.logger.info("Batch processing completed")
        self.logger.info(f"Summary: {stats['completed']} completed, {stats['failed']} failed, {stats['skipped']} skipped")
        self.logger.info(f"Total time: {total_time:.2f}s, Throughput: {stats['throughput']:.2f} files/s")
        
        return {
            'summary': stats,
            'results': self.results,
            'completed': completed_results,
            'failed': failed_results
        }


class BatchProcessingCLI:
    """Command-line interface for batch processing."""
    
    def __init__(self):
        self.processor = None
    
    async def run(self, args: List[str]):
        """Run the CLI with provided arguments."""
        import argparse
        
        parser = argparse.ArgumentParser(description='Docling MCP Batch Processor')
        parser.add_argument('files', nargs='+', help='Files to process')
        parser.add_argument('--format', default='markdown', choices=['markdown', 'text', 'json'],
                          help='Output format')
        parser.add_argument('--max-concurrent', type=int, default=5,
                          help='Maximum concurrent processing')
        parser.add_argument('--chunk-size', type=int, default=10,
                          help='Chunk size for processing')
        parser.add_argument('--retry-attempts', type=int, default=3,
                          help='Number of retry attempts')
        parser.add_argument('--output-dir', help='Output directory for results')
        parser.add_argument('--progress', action='store_true',
                          help='Show progress information')
        
        args = parser.parse_args(args)
        
        # Configure batch processing
        config = BatchProcessingConfig(
            max_concurrent=args.max_concurrent,
            chunk_size=args.chunk_size,
            retry_attempts=args.retry_attempts,
            enable_progress_callback=args.progress
        )
        
        # Create processor
        # Note: This would need an actual MCP client instance
        # self.processor = BatchProcessor(mcp_client, config)
        
        # Process files
        # results = await self.processor.process_batch(args.files, args.format)
        
        print(f"Would process {len(args.files)} files with format {args.format}")
        print("Note: This is a demonstration. Connect to actual MCP client for full functionality.")


async def progress_callback(progress_data: Dict[str, Any]):
    """Example progress callback function."""
    percentage = progress_data['percentage']
    processed = progress_data['processed']
    total = progress_data['total']
    elapsed = progress_data['elapsed_time']
    
    print(f"\rProgress: {percentage:.1f}% ({processed}/{total} files) - {elapsed:.1f}s", end="")


async def main():
    """Main example function."""
    # This would be used with an actual MCP client
    print("Batch processing example - requires MCP client connection")
    print("See basic_client.py for MCP client implementation")


if __name__ == "__main__":
    asyncio.run(main())