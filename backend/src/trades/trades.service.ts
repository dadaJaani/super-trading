import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Signal } from '../entities/signal.entity';
import { Trade } from '../entities/trade.entity';

@Injectable()
export class TradesService {
  constructor(
    @InjectRepository(Trade)
    private readonly tradesRepository: Repository<Trade>,
    @InjectRepository(Signal)
    private readonly signalsRepository: Repository<Signal>,
  ) {}

  findTradesByBot(botId: string, status?: string): Promise<Trade[]> {
    const where: { botId: string; status?: string } = { botId };
    if (status) {
      where.status = status;
    }
    return this.tradesRepository.find({
      where,
      order: { openTime: 'DESC' },
    });
  }

  findSignalsByBot(botId: string, limit?: number): Promise<Signal[]> {
    return this.signalsRepository.find({
      where: { botId },
      order: { time: 'DESC' },
      take: limit ?? 50,
    });
  }
}
