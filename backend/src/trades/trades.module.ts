import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Signal } from '../entities/signal.entity';
import { Trade } from '../entities/trade.entity';
import { TradesController } from './trades.controller';
import { TradesService } from './trades.service';

@Module({
  imports: [TypeOrmModule.forFeature([Trade, Signal])],
  controllers: [TradesController],
  providers: [TradesService],
})
export class TradesModule {}
