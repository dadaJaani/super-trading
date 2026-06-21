import { Controller, Get, Query } from '@nestjs/common';
import { CandlesService } from './candles.service';

@Controller('candles')
export class CandlesController {
  constructor(private readonly candlesService: CandlesService) {}

  @Get()
  findCandles(
    @Query('instrument') instrument = 'XAU_USD',
    @Query('granularity') granularity = 'M5',
    @Query('limit') limit?: string,
  ) {
    const parsed = limit ? parseInt(limit, 10) : 120;
    return this.candlesService.findCandles(instrument, granularity, parsed);
  }
}
