import { Controller, Get, Param, Query } from '@nestjs/common';
import { TradesService } from './trades.service';

@Controller('bots/:botId')
export class TradesController {
  constructor(private readonly tradesService: TradesService) {}

  @Get('trades')
  findTrades(@Param('botId') botId: string, @Query('status') status?: string) {
    return this.tradesService.findTradesByBot(botId, status);
  }

  @Get('signals')
  findSignals(@Param('botId') botId: string, @Query('limit') limit?: string) {
    const parsed = limit ? parseInt(limit, 10) : 50;
    return this.tradesService.findSignalsByBot(botId, parsed);
  }
}
