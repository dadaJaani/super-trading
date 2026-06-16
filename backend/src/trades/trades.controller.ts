import { Controller, Get, Param } from '@nestjs/common';
import { TradesService } from './trades.service';

@Controller('bots/:botId')
export class TradesController {
  constructor(private readonly tradesService: TradesService) {}

  @Get('trades')
  findTrades(@Param('botId') botId: string) {
    return this.tradesService.findTradesByBot(botId);
  }

  @Get('signals')
  findSignals(@Param('botId') botId: string) {
    return this.tradesService.findSignalsByBot(botId);
  }
}
