import { Controller, Get, Query } from '@nestjs/common';
import { PerformanceService } from './performance.service';

@Controller('performance')
export class PerformanceController {
  constructor(private readonly performanceService: PerformanceService) {}

  @Get()
  getPerformance() {
    return this.performanceService.getAggregatePerformance();
  }

  @Get('balance')
  getBalanceHistory(@Query('limit') limit?: string) {
    const parsed = limit ? parseInt(limit, 10) : 500;
    return this.performanceService.getBalanceHistory(parsed);
  }
}
