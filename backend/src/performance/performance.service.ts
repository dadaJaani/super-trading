import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Trade } from '../entities/trade.entity';

@Injectable()
export class PerformanceService {
  constructor(
    @InjectRepository(Trade)
    private readonly tradesRepository: Repository<Trade>,
  ) {}

  async getAggregatePerformance() {
    const trades = await this.tradesRepository.find({
      where: { status: 'closed' },
    });

    const totalPnl = trades.reduce(
      (sum, trade) => sum + Number(trade.pnl ?? 0),
      0,
    );

    return {
      totalPnl,
      closedTrades: trades.length,
      winRate: trades.length
        ? trades.filter((t) => Number(t.pnl ?? 0) > 0).length / trades.length
        : 0,
    };
  }
}
